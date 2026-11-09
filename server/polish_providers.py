"""One interface for AI polishing and profile drafts, with pluggable model providers.

Configuration (environment variables override the optional JSON file):
  QINGHE_POLISH_PROVIDER     local (default) | openai | anthropic | any registered name
  QINGHE_POLISH_MODEL        model name, required by remote providers
  QINGHE_POLISH_BASE_URL     API root, e.g. http://localhost:11434/v1 for Ollama
  QINGHE_POLISH_TIMEOUT      seconds per network operation, default 20
  QINGHE_POLISH_FALLBACK     local (default) falls back to the local engine on failure; off returns an error
  QINGHE_POLISH_OPTIONS      JSON object merged into the request body, e.g. {"temperature": 0.7}
  QINGHE_POLISH_API_KEY_ENV  name of the variable holding the key, default QINGHE_POLISH_API_KEY
  QINGHE_POLISH_CONFIG       JSON file path, default server/ai_polish.local.json (git-ignored)

API keys are read only from environment variables, never from the config file.
To add a provider, subclass PolishProvider, implement polish() and draft(), and decorate it with @register('name').
Profile drafts ask the model for JSON only. parse_draft() rejects anything that is not a grounded itinerary.
"""
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ai_draft import GENERIC_PLACES, PACKAGE_KEYS, draft_profile, mentioned_places, package_plan
from ai_polish import LIMITS, clip_text, polish_text

CONFIG_FILE = Path(__file__).resolve().parent / 'ai_polish.local.json'
ENV_PREFIX = 'QINGHE_POLISH_'
SETTING_KEYS = ('provider', 'model', 'base_url', 'timeout', 'fallback', 'options', 'api_key_env')
SECRET_WORDS = ('key', 'token', 'secret', 'password')
MAX_RESPONSE_BYTES = 1_000_000


class PolishError(Exception):
    """A provider failure. str(error) is a log detail; .message is safe to show users."""
    status = 502
    message = 'AI 润色服务暂时不可用，请稍后再试'


class ProviderConfigError(PolishError):
    status = 503
    message = 'AI 润色服务未正确配置'


class ProviderTimeout(PolishError):
    status = 504
    message = 'AI 润色服务响应超时，请稍后再试'


class ProviderResponseError(PolishError):
    pass


@dataclass(frozen=True)
class PolishRequest:
    text: str
    scene: str
    city: str = ''
    variant: int = 0

    @property
    def limit(self):
        return LIMITS[self.scene]


@dataclass(frozen=True)
class PolishResult:
    text: str
    provider: str
    model: str = ''
    fallback_from: str = ''

    def to_json(self):
        result = dict(text=self.text, engine=self.provider, provider=self.provider, model=self.model)
        if self.fallback_from:
            result['fallbackFrom'] = self.fallback_from
        return result


@dataclass(frozen=True)
class Settings:
    provider: str = 'local'
    model: str = ''
    base_url: str = ''
    timeout: float = 20.0
    fallback: bool = True
    options: dict = field(default_factory=dict)
    api_key_env: str = 'QINGHE_POLISH_API_KEY'
    api_key: str = field(default='', repr=False)


PROVIDERS = {}


def register(name):
    def decorate(cls):
        cls.name = name
        PROVIDERS[name] = cls
        return cls
    return decorate


class DraftSchemaError(ValueError):
    """Provider or client JSON failed structural checks. str(error) is safe to log or show on publish."""


@dataclass(frozen=True)
class DraftRequest:
    notes: str
    city: str = ''
    services: tuple = ()
    packages: tuple = ()
    part: str = 'all'
    variant: int = 0


@dataclass(frozen=True)
class DraftResult:
    payload: dict
    provider: str
    model: str = ''
    fallback_from: str = ''

    def to_json(self):
        result = dict(self.payload)
        result.update(provider=self.provider, model=self.model, engine=self.provider, fallbackFrom=self.fallback_from)
        return result


class PolishProvider:
    """Base class: subclasses return raw model text from polish() and draft(); the service validates it."""
    name = ''
    default_base_url = ''
    needs_model = True
    needs_key = False

    def __init__(self, settings):
        self.settings = settings
        self.model = settings.model
        self.base_url = (settings.base_url or self.default_base_url).rstrip('/')
        if self.needs_model and not self.model:
            raise ProviderConfigError(f'{self.name} 需要设置 QINGHE_POLISH_MODEL')
        if self.needs_key and not settings.api_key:
            raise ProviderConfigError(f'{self.name} 需要在环境变量 {settings.api_key_env} 中提供 API 密钥')

    def polish(self, request):
        raise NotImplementedError

    def draft(self, request):
        raise NotImplementedError

    def finish(self, raw, request):
        """Turn raw provider output into final text; remote output is cleaned and clipped."""
        return clean_output(raw, request.limit)

    def finish_draft(self, raw, request):
        """Turn raw provider output into a validated draft. Dict output is accepted for the local engine."""
        return parse_draft(raw, request)

    def post_json(self, path, payload, headers=None):
        request = urllib.request.Request(
            self.base_url + path, method='POST',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                     'User-Agent': 'qinghe-polish/1.0', **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            detail = error.read(300).decode('utf-8', 'replace').strip()
            raise ProviderResponseError(f'HTTP {error.code}: {detail}') from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ProviderTimeout(f'连接超时（{self.settings.timeout:g} 秒）') from None
            raise ProviderResponseError(f'无法连接 {self.base_url}: {error.reason}') from None
        except TimeoutError:
            raise ProviderTimeout(f'读取超时（{self.settings.timeout:g} 秒）') from None
        except (OSError, http.client.HTTPException) as error:
            raise ProviderResponseError(f'网络错误：{type(error).__name__}') from None
        if len(body) > MAX_RESPONSE_BYTES:
            raise ProviderResponseError('响应过大')
        try:
            result = json.loads(body)
        except ValueError:
            raise ProviderResponseError('响应不是合法的 JSON') from None
        if not isinstance(result, dict):
            raise ProviderResponseError('响应格式不正确')
        return result


@register('local')
class LocalProvider(PolishProvider):
    """The built-in rule engine; needs no network, model or key."""
    needs_model = False

    def polish(self, request):
        return polish_text(request.text, request.scene, request.city, request.variant)

    def draft(self, request):
        return draft_profile(request.notes, request.city, request.services, request.packages, request.part, request.variant)

    def finish(self, raw, request):
        return raw  # already normalized and clipped by the engine


@register('openai')
class OpenAICompatibleProvider(PolishProvider):
    """Any OpenAI-compatible /chat/completions API: OpenAI, Ollama, vLLM, DeepSeek, Claude's compatibility endpoint, etc."""
    default_base_url = 'https://api.openai.com/v1'

    def polish(self, request):
        headers = {'Authorization': 'Bearer ' + self.settings.api_key} if self.settings.api_key else {}
        payload = dict(model=self.model, messages=[
            dict(role='system', content=system_prompt(request)),
            dict(role='user', content=request.text)], **self.settings.options)
        result = self.post_json('/chat/completions', payload, headers)
        try:
            return result['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError):
            raise ProviderResponseError('响应缺少 choices[0].message.content') from None

    def draft(self, request):
        headers = {'Authorization': 'Bearer ' + self.settings.api_key} if self.settings.api_key else {}
        payload = dict(model=self.model, messages=[
            dict(role='system', content=draft_system_prompt(request)),
            dict(role='user', content=draft_user_prompt(request))], **self.settings.options)
        result = self.post_json('/chat/completions', payload, headers)
        try:
            return result['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError):
            raise ProviderResponseError('响应缺少 choices[0].message.content') from None


@register('anthropic')
class AnthropicProvider(PolishProvider):
    """Claude through the native Messages API."""
    default_base_url = 'https://api.anthropic.com/v1'
    needs_key = True

    def polish(self, request):
        payload = dict(model=self.model, max_tokens=1024, system=system_prompt(request),
                       messages=[dict(role='user', content=request.text)], **self.settings.options)
        result = self.post_json('/messages', payload, {'x-api-key': self.settings.api_key, 'anthropic-version': '2023-06-01'})
        blocks = result.get('content')
        parts = [b.get('text') for b in blocks if isinstance(b, dict) and b.get('type') == 'text'] if isinstance(blocks, list) else []
        if not parts or not all(isinstance(p, str) for p in parts):
            raise ProviderResponseError('响应缺少文本内容')
        return ''.join(parts)

    def draft(self, request):
        payload = dict(model=self.model, max_tokens=2048, system=draft_system_prompt(request),
                       messages=[dict(role='user', content=draft_user_prompt(request))], **self.settings.options)
        result = self.post_json('/messages', payload, {'x-api-key': self.settings.api_key, 'anthropic-version': '2023-06-01'})
        blocks = result.get('content')
        parts = [b.get('text') for b in blocks if isinstance(b, dict) and b.get('type') == 'text'] if isinstance(blocks, list) else []
        if not parts or not all(isinstance(p, str) for p in parts):
            raise ProviderResponseError('响应缺少文本内容')
        return ''.join(parts)


def system_prompt(request):
    guide = request.scene == 'guide'
    place = request.city if request.city and request.city != '全国' else '这座城市'
    rules = [
        f'你是「青禾 · 城市轻兼职」网站的文字润色助手，请润色用户发来的{"地陪服务介绍" if guide else "个人简介"}。',
        '1. 保留全部事实（地点、时间、数字、经历、爱好），不编造新的经历、资质或承诺。',
        '2. 保持第一人称和原本的语气，让句子更自然、更有温度，使用中文全角标点。',
        f'3. 全文不超过 {request.limit} 个字。' + (f'可以分成两段，面向想来{place}的旅人。' if guide else ''),
        '4. 只输出润色后的正文，不要标题、解释、引号或 Markdown。',
    ]
    if request.variant:
        rules.append(f'这是第 {request.variant + 1} 次润色，请换一种和之前不同的表达。')
    return '\n'.join(rules)


def clean_output(value, limit):
    """Strip wrappers models like to add, reject empty output, and enforce the length limit."""
    if not isinstance(value, str):
        raise ProviderResponseError('模型返回的内容不是文本')
    value = re.sub(r'<think>.*?</think>', '', value.replace('\r\n', '\n'), flags=re.S).strip()
    value = re.sub(r'^```[\w-]*\n?|\n?```$', '', value).strip()
    value = re.sub(r'^(润色后|润色结果)[：:]\s*', '', value)
    while len(value) >= 2 and (value[0], value[-1]) in {('"', '"'), ('“', '”'), ('「', '」')}:
        value = value[1:-1].strip()
    value = re.sub(r'\n{3,}', '\n\n', value)
    if not value:
        raise ProviderResponseError('模型返回了空内容')
    return clip_text(value, limit)


def load_settings(env=None):
    env = os.environ if env is None else env
    explicit = env.get(ENV_PREFIX + 'CONFIG', '').strip()
    path = Path(explicit) if explicit else CONFIG_FILE
    values = {}
    if explicit or path.is_file():
        try:
            values = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise ProviderConfigError(f'无法读取配置文件 {path.name}：{error}') from None
        if not isinstance(values, dict):
            raise ProviderConfigError(f'配置文件 {path.name} 必须是 JSON 对象')
        secrets = sorted(k for k in values if k != 'api_key_env' and any(w in k.lower() for w in SECRET_WORDS))
        if secrets:
            raise ProviderConfigError(f'配置文件不能包含密钥字段 {secrets}，请改用环境变量')
        unknown = sorted(set(values) - set(SETTING_KEYS))
        if unknown:
            raise ProviderConfigError(f'配置文件包含未知字段 {unknown}')
    for key in SETTING_KEYS:
        if env.get(ENV_PREFIX + key.upper(), '').strip():
            values[key] = env[ENV_PREFIX + key.upper()].strip()

    options = values.get('options') or {}
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except ValueError:
            raise ProviderConfigError('QINGHE_POLISH_OPTIONS 必须是 JSON 对象') from None
    if not isinstance(options, dict):
        raise ProviderConfigError('options 必须是 JSON 对象')
    try:
        timeout = float(values.get('timeout', Settings.timeout))
    except (TypeError, ValueError):
        timeout = 0
    if not 0 < timeout <= 300:
        raise ProviderConfigError('timeout 必须是 0 到 300 之间的秒数')
    key_env = str(values.get('api_key_env') or Settings.api_key_env)
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key_env):
        raise ProviderConfigError('api_key_env 必须是环境变量名')
    return Settings(
        provider=str(values.get('provider') or 'local').strip().lower(),
        model=str(values.get('model') or '').strip(),
        base_url=str(values.get('base_url') or '').strip(),
        timeout=timeout,
        fallback=str(values.get('fallback', 'local')).strip().lower() not in {'off', 'false', '0', 'no', 'none'},
        options=options, api_key_env=key_env, api_key=env.get(key_env, '').strip())


def create_provider(settings):
    cls = PROVIDERS.get(settings.provider)
    if not cls:
        raise ProviderConfigError(f'未知的润色提供方 {settings.provider!r}，可选：{", ".join(sorted(PROVIDERS))}')
    return cls(settings)


def polish(text, scene, city='', variant=0, env=None):
    """Polish with the configured provider; on failure fall back to the local engine unless disabled."""
    request = PolishRequest(text, scene, city, int(variant))
    settings = None
    try:
        settings = load_settings(env)
        provider = create_provider(settings)
        try:
            final = provider.finish(provider.polish(request), request)
        except PolishError:
            raise
        except Exception as error:  # third-party providers must not crash the request
            raise ProviderResponseError(f'{type(error).__name__}: {error}') from None
        return PolishResult(final, provider.name, provider.model)
    except PolishError as error:
        source = settings.provider if settings else 'config'
        if settings and not settings.fallback:
            print(f'[ai-polish] {source} 失败：{error}', file=sys.stderr)
            raise
        print(f'[ai-polish] {source} 失败，已改用本地引擎：{error}', file=sys.stderr)
        local = LocalProvider(Settings())
        return PolishResult(local.finish(local.polish(request), request), local.name, fallback_from=source)


PART_FIELDS = {
    'all': ('bio', 'highlights', 'itineraries'),
    'bio': ('bio',),
    'highlights': ('highlights',),
    'itinerary': ('itineraries',),
}
KNOWN_DRAFT_FIELDS = {'bio', 'highlights', 'itineraries'}
NODE_FIELDS = {'time', 'place', 'activity'}
TIME_RE = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')


def draft_system_prompt(request):
    """Ask the model for one JSON object and nothing else. Places must come from the notes."""
    place = request.city if request.city and request.city != '全国' else '这座城市'
    packages = '；'.join(f"{item['name']}（{item['key']}，{item['duration']}）" for item in request.packages)
    blocks = {
        'bio': '这次只重写简介：JSON 里必须有 bio，不要加别的未知字段。',
        'highlights': '这次只重写亮点：JSON 里必须有 highlights，不要加别的未知字段。',
        'itinerary': '这次只重写行程：JSON 里必须有 itineraries，不要加别的未知字段。',
    }
    rules = [
        '你是「青禾 · 城市轻兼职」的地陪主页撰写助手。只输出一个 JSON 对象，不要 Markdown、解释或代码块。',
        f'面向想来{place}的旅人。第一人称，温暖，不夸张。不写价格、资质和安全承诺。',
        '1. 只能使用用户原文里出现的地点、经历和爱好。可以安排顺序、时间和衔接，但不要新增具体店名或景点。',
        '2. 素材不够时，地点用「沿途散步」「自由拍照」「根据你的兴趣现场调整」，不要编地名。',
        '3. 每个行程 3 到 5 个节点。time 用 24 小时制 HH:MM，严格递增，首尾间隔不超过套餐时长。傍晚套餐从 17:00 或更晚开始。',
        '4. bio 不超过 600 字。highlights 正好 3 条，每条不超过 20 字。节点只有 time、place、activity 三个字段。',
        f'5. 套餐：{packages}。itineraries 的键就是这些套餐的 key。',
        blocks.get(request.part, 'JSON 只包含 bio、highlights、itineraries 三个字段。'),
    ]
    if request.variant:
        rules.append(f'这是第 {request.variant + 1} 版，请换一种写法，不要重复上一版的句式和时间安排。')
    return '\n'.join(rules)


def draft_user_prompt(request):
    lines = [f'城市：{request.city}', f'原文：{request.notes}']
    if request.services:
        lines.append('服务：' + '、'.join(request.services))
    lines.append('请只输出 JSON。')
    return '\n'.join(lines)


def decode_draft_json(raw):
    if not isinstance(raw, str):
        raise DraftSchemaError('模型返回的内容不是文本')
    value = re.sub(r'<think>.*?</think>', '', raw, flags=re.S).strip()
    fenced = re.fullmatch(r'```[A-Za-z0-9_-]*\s*([\s\S]*?)\s*```', value)
    if fenced:
        value = fenced.group(1).strip()
    try:
        data = json.loads(value)
    except ValueError:
        raise DraftSchemaError('模型返回的不是合法 JSON') from None
    if not isinstance(data, dict):
        raise DraftSchemaError('模型返回的 JSON 必须是对象')
    return data


def clean_bio(value):
    if not isinstance(value, str):
        raise DraftSchemaError('简介必须是字符串')
    value = value.strip()
    if not value or len(value) > 600:
        raise DraftSchemaError('简介不能超过 600 字')
    return value


def clean_highlights(value):
    if not isinstance(value, list) or len(value) != 3:
        raise DraftSchemaError('亮点需要正好 3 条')
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            raise DraftSchemaError('亮点必须是字符串')
        item = re.sub(r'\s+', ' ', item).strip()
        if not item or len(item) > 20:
            raise DraftSchemaError('每条亮点需要 1 到 20 个字')
        cleaned.append(item)
    return cleaned


def clean_phrase(value, limit, label):
    if not isinstance(value, str):
        raise DraftSchemaError(f'{label}必须是字符串')
    value = value.strip()
    if not value or len(value) > limit:
        raise DraftSchemaError(f'{label}长度不正确')
    return value


def place_is_grounded(place, activity, notes):
    if place not in GENERIC_PLACES and place not in notes:
        return False
    for text in (place, activity):
        for name in mentioned_places(text):
            if name not in notes and name not in GENERIC_PLACES:
                return False
    return True


def clean_node(node, notes, grounding):
    if not isinstance(node, dict) or set(node) != NODE_FIELDS:
        raise DraftSchemaError('行程节点格式不正确')
    if not isinstance(node['time'], str):
        raise DraftSchemaError('行程时间需要是 HH:MM')
    match = TIME_RE.fullmatch(node['time'].strip().replace('：', ':'))
    if not match:
        raise DraftSchemaError('行程时间需要是 HH:MM')
    place = clean_phrase(node['place'], 20, '地点')
    activity = clean_phrase(node['activity'], 80, '活动')
    if grounding and not place_is_grounded(place, activity, notes):
        raise DraftSchemaError('行程出现了原文里没有的地点')
    return dict(time=f'{match[1]}:{match[2]}', place=place, activity=activity)


def check_schedule(nodes, package):
    minutes = []
    for node in nodes:
        hour, minute = (int(part) for part in node['time'].split(':'))
        minutes.append(hour * 60 + minute)
    if any(later <= earlier for earlier, later in zip(minutes, minutes[1:])):
        raise DraftSchemaError('行程时间必须递增')
    if minutes[-1] - minutes[0] > package['hours'] * 60:
        raise DraftSchemaError('行程超出套餐时长')
    if package['key'] == 'evening' and minutes[0] < 17 * 60:
        raise DraftSchemaError('傍晚行程需要从 17:00 开始或更晚')


def clean_itineraries(value, request, grounding):
    if not isinstance(value, dict):
        raise DraftSchemaError('行程格式不正确')
    expected = tuple(package['key'] for package in request.packages)
    if set(value) != set(expected):
        raise DraftSchemaError('行程套餐不正确')
    by_key = {package['key']: package for package in request.packages}
    cleaned = {}
    for key in expected:
        nodes = value[key]
        if not isinstance(nodes, list) or not 3 <= len(nodes) <= 5:
            raise DraftSchemaError('每个行程需要 3 到 5 个节点')
        cleaned[key] = [clean_node(node, request.notes, grounding) for node in nodes]
        check_schedule(cleaned[key], by_key[key])
    return cleaned


def validate_draft(data, request, grounding=True):
    if not isinstance(data, dict):
        raise DraftSchemaError('模型返回的 JSON 必须是对象')
    fields = PART_FIELDS.get(request.part)
    if not fields:
        raise DraftSchemaError('生成范围不正确')
    if set(data) - KNOWN_DRAFT_FIELDS:
        raise DraftSchemaError('返回了多余字段')
    if any(name not in data for name in fields):
        raise DraftSchemaError('返回缺少字段')
    result = {}
    if 'bio' in fields:
        result['bio'] = clean_bio(data['bio'])
    if 'highlights' in fields:
        result['highlights'] = clean_highlights(data['highlights'])
    if 'itineraries' in fields:
        result['itineraries'] = clean_itineraries(data['itineraries'], request, grounding)
    return result


def parse_draft(raw, request):
    """Strip model wrappers, parse JSON, and reject a draft that breaks the schema or grounding rules."""
    try:
        data = raw if isinstance(raw, dict) else decode_draft_json(raw)
        return validate_draft(data, request, grounding=True)
    except DraftSchemaError as error:
        raise ProviderResponseError(str(error)) from None


def validate_highlights(value):
    request = DraftRequest('', part='highlights')
    return validate_draft({'highlights': value}, request, grounding=False)['highlights']


def validate_itineraries(value):
    request = DraftRequest('', part='itinerary', packages=tuple(package_plan(PACKAGE_KEYS)))
    return validate_draft({'itineraries': value}, request, grounding=False)['itineraries']


def draft(notes, city='', services=(), packages=None, part='all', variant=0, env=None):
    """Draft with the configured provider; on failure fall back to the local engine unless disabled."""
    plans = tuple(package_plan(packages or PACKAGE_KEYS, variant))
    request = DraftRequest(notes, city, tuple(services), plans, part, int(variant))
    settings = None
    try:
        settings = load_settings(env)
        provider = create_provider(settings)
        try:
            final = provider.finish_draft(provider.draft(request), request)
        except PolishError:
            raise
        except Exception as error:  # third-party providers must not crash the request
            raise ProviderResponseError(f'{type(error).__name__}: {error}') from None
        return DraftResult(final, provider.name, provider.model)
    except PolishError as error:
        source = settings.provider if settings else 'config'
        if settings and not settings.fallback:
            print(f'[ai-draft] {source} 失败：{error}', file=sys.stderr)
            raise
        print(f'[ai-draft] {source} 失败，已改用本地引擎：{error}', file=sys.stderr)
        local = LocalProvider(Settings())
        return DraftResult(local.finish_draft(local.draft(request), request), local.name, fallback_from=source)
