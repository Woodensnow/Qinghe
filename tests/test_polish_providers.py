"""AI polish provider interface: fake providers and local stub servers only, never real model APIs."""
import json
import os
import socket
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import polish_providers as pp
from test_server import ApiFixture

TEXT = '我在苏州住了3年,每周六带大家散步,喜欢咖啡和老街'


class StubModel:
    """A local HTTP server that answers like a model API and records each request."""

    def __init__(self, reply=None, status=200, delay=0, raw=None):
        self.reply, self.status, self.delay, self.raw = reply, status, delay, raw
        self.requests, self.release = [], threading.Event()
        self.release.set()
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                stub.requests.append(dict(path=self.path, headers={k.lower(): v for k, v in self.headers.items()}, body=body))
                stub.release.wait(5)
                time.sleep(stub.delay)
                content = stub.raw if stub.raw is not None else json.dumps(stub.reply).encode()
                try:
                    self.send_response(stub.status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:%d/v1' % self.http.server_address[1]
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def close(self):
        self.release.set()
        self.http.shutdown()
        self.http.server_close()


def openai_reply(text):
    return dict(choices=[dict(message=dict(role='assistant', content=text))])


@contextmanager
def stub(**kwargs):
    model = StubModel(**kwargs)
    try:
        yield model
    finally:
        model.close()


class ProviderTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(pp, 'CONFIG_FILE', Path(self.temp.name) / 'ai_polish.local.json')
        patcher.start()
        self.addCleanup(patcher.stop)
        proxies = patch.dict(os.environ, {'NO_PROXY': '*', 'no_proxy': '*'})
        proxies.start()
        self.addCleanup(proxies.stop)
        self.stderr = patch('sys.stderr')  # keep expected failure logs out of test output
        self.stderr.start()
        self.addCleanup(self.stderr.stop)

    def write_config(self, values):
        pp.CONFIG_FILE.write_text(json.dumps(values), encoding='utf-8')


class SettingsTests(ProviderTestCase):
    def test_defaults_to_local_without_any_config(self):
        settings = pp.load_settings({})
        self.assertEqual((settings.provider, settings.timeout, settings.fallback), ('local', 20.0, True))
        result = pp.polish(TEXT, 'profile', env={})
        self.assertEqual((result.provider, result.model, result.fallback_from), ('local', '', ''))
        self.assertEqual(result.text, pp.polish_text(TEXT, 'profile'))

    def test_environment_overrides_config_file_and_key_comes_from_environment(self):
        self.write_config(dict(provider='openai', model='file-model', base_url='http://file', timeout=5, api_key_env='MY_KEY'))
        settings = pp.load_settings({'QINGHE_POLISH_MODEL': 'env-model', 'MY_KEY': 'sk-test'})
        self.assertEqual((settings.provider, settings.model, settings.base_url, settings.timeout), ('openai', 'env-model', 'http://file', 5.0))
        self.assertEqual(settings.api_key, 'sk-test')
        self.assertNotIn('sk-test', repr(settings))

    def test_config_file_rejects_secrets_and_unknown_fields(self):
        for values in (dict(provider='openai', api_key='sk-x'), dict(provider='openai', token='x'), dict(modle='typo')):
            self.write_config(values)
            with self.assertRaises(pp.ProviderConfigError):
                pp.load_settings({})

    def test_invalid_values_are_config_errors(self):
        for env in ({'QINGHE_POLISH_TIMEOUT': 'soon'}, {'QINGHE_POLISH_TIMEOUT': '0'},
                    {'QINGHE_POLISH_OPTIONS': '[1]'}, {'QINGHE_POLISH_OPTIONS': '{bad'},
                    {'QINGHE_POLISH_API_KEY_ENV': 'not a name'}, {'QINGHE_POLISH_CONFIG': '/missing/polish.json'}):
            with self.assertRaises(pp.ProviderConfigError, msg=env):
                pp.load_settings(env)
        self.assertFalse(pp.load_settings({'QINGHE_POLISH_FALLBACK': 'off'}).fallback)
        self.assertEqual(pp.load_settings({'QINGHE_POLISH_OPTIONS': '{"temperature": 0.7}'}).options, {'temperature': 0.7})

    def test_remote_providers_require_model_and_anthropic_requires_key(self):
        for env in ({'QINGHE_POLISH_PROVIDER': 'openai'},
                    {'QINGHE_POLISH_PROVIDER': 'anthropic', 'QINGHE_POLISH_MODEL': 'claude-haiku-5-5'},
                    {'QINGHE_POLISH_PROVIDER': 'nope'}):
            with self.assertRaises(pp.ProviderConfigError, msg=env):
                pp.create_provider(pp.load_settings(env))


class ServiceTests(ProviderTestCase):
    def register(self, name, behaviour):
        @pp.register(name)
        class FakeProvider(pp.PolishProvider):
            def polish(self, request):
                return behaviour(request)
        self.addCleanup(pp.PROVIDERS.pop, name)
        return FakeProvider

    def test_new_provider_only_needs_a_registered_class(self):
        seen = []
        self.register('fake', lambda request: seen.append(request) or '```\n“我在苏州住了三年，每周六带大家散步。”\n```')
        result = pp.polish(TEXT, 'guide', '苏州', 2.0, env={'QINGHE_POLISH_PROVIDER': 'fake', 'QINGHE_POLISH_MODEL': 'fake-1'})
        self.assertEqual(result.to_json(), dict(text='我在苏州住了三年，每周六带大家散步。', engine='fake', provider='fake', model='fake-1'))
        self.assertEqual((seen[0].scene, seen[0].city, seen[0].variant, seen[0].limit), ('guide', '苏州', 2, 600))

    def test_output_is_cleaned_and_clipped_to_the_scene_limit(self):
        self.register('wordy', lambda request: '<think>先想想</think>润色后：' + '我喜欢在老街散步。' * 40)
        result = pp.polish(TEXT, 'profile', env={'QINGHE_POLISH_PROVIDER': 'wordy', 'QINGHE_POLISH_MODEL': 'w'})
        self.assertLessEqual(len(result.text), 160)
        self.assertTrue(result.text.startswith('我喜欢') and result.text.endswith('。'))

    def test_failures_fall_back_to_local_engine_by_default(self):
        self.register('broken', lambda request: 1 / 0)
        self.register('empty', lambda request: '  ')
        for env in ({'QINGHE_POLISH_PROVIDER': 'broken', 'QINGHE_POLISH_MODEL': 'b'},
                    {'QINGHE_POLISH_PROVIDER': 'empty', 'QINGHE_POLISH_MODEL': 'e'},
                    {'QINGHE_POLISH_PROVIDER': 'openai'}):
            result = pp.polish(TEXT, 'profile', env=env)
            self.assertEqual((result.provider, result.fallback_from), ('local', env['QINGHE_POLISH_PROVIDER']))
            self.assertEqual(result.text, pp.polish_text(TEXT, 'profile'))
        self.write_config([])
        self.assertEqual(pp.polish(TEXT, 'profile', env={}).fallback_from, 'config')

    def test_fallback_off_raises_a_typed_error(self):
        self.register('broken', lambda request: {}['missing'])
        env = {'QINGHE_POLISH_PROVIDER': 'broken', 'QINGHE_POLISH_MODEL': 'b', 'QINGHE_POLISH_FALLBACK': 'off'}
        with self.assertRaises(pp.ProviderResponseError) as caught:
            pp.polish(TEXT, 'profile', env=env)
        self.assertEqual(caught.exception.status, 502)
        with self.assertRaises(pp.ProviderConfigError):
            pp.polish(TEXT, 'profile', env={'QINGHE_POLISH_PROVIDER': 'openai', 'QINGHE_POLISH_FALLBACK': 'off'})


class HttpProviderTests(ProviderTestCase):
    def env(self, model, **extra):
        values = {'QINGHE_POLISH_PROVIDER': 'openai', 'QINGHE_POLISH_MODEL': 'qwen2.5:7b',
                  'QINGHE_POLISH_BASE_URL': model.url, 'QINGHE_POLISH_FALLBACK': 'off'}
        values.update(extra)
        return values

    def test_openai_compatible_request_and_response(self):
        with stub(reply=openai_reply('我在苏州住了三年，每周六带大家散步，也喜欢咖啡和老街。')) as model:
            env = self.env(model, QINGHE_POLISH_API_KEY='sk-local-test', QINGHE_POLISH_OPTIONS='{"temperature": 0.6}')
            result = pp.polish(TEXT, 'guide', '苏州', 1, env=env)
        self.assertEqual((result.provider, result.model), ('openai', 'qwen2.5:7b'))
        self.assertEqual(result.text, '我在苏州住了三年，每周六带大家散步，也喜欢咖啡和老街。')
        sent = model.requests[0]
        self.assertEqual(sent['path'], '/v1/chat/completions')
        self.assertEqual(sent['headers']['authorization'], 'Bearer sk-local-test')
        self.assertEqual((sent['body']['model'], sent['body']['temperature']), ('qwen2.5:7b', 0.6))
        system, user = sent['body']['messages']
        self.assertEqual((system['role'], user['role'], user['content']), ('system', 'user', TEXT))
        for rule in ('不编造', '600', '苏州', '第 2 次'):
            self.assertIn(rule, system['content'])

    def test_openai_compatible_works_without_a_key_for_local_servers(self):
        with stub(reply=openai_reply('我在苏州住了三年。')) as model:
            pp.polish(TEXT, 'profile', env=self.env(model))
        self.assertNotIn('authorization', model.requests[0]['headers'])

    def test_anthropic_messages_api(self):
        reply = dict(content=[dict(type='text', text='我在苏州住了三年，'), dict(type='text', text='每周六带大家散步。')])
        with stub(reply=reply) as model:
            env = self.env(model, QINGHE_POLISH_PROVIDER='anthropic', QINGHE_POLISH_MODEL='claude-haiku-5-5',
                           QINGHE_POLISH_API_KEY_ENV='ANTHROPIC_API_KEY', ANTHROPIC_API_KEY='sk-ant-test')
            result = pp.polish(TEXT, 'profile', env=env)
        self.assertEqual((result.text, result.provider), ('我在苏州住了三年，每周六带大家散步。', 'anthropic'))
        sent = model.requests[0]
        self.assertEqual(sent['path'], '/v1/messages')
        self.assertEqual((sent['headers']['x-api-key'], sent['headers']['anthropic-version']), ('sk-ant-test', '2023-06-01'))
        self.assertEqual((sent['body']['model'], sent['body']['max_tokens']), ('claude-haiku-5-5', 1024))
        self.assertIn('160', sent['body']['system'])

    def test_timeouts_and_bad_responses_are_typed_errors(self):
        cases = [(dict(reply=openai_reply('慢'), delay=1), pp.ProviderTimeout),
                 (dict(reply={'error': 'boom'}, status=500), pp.ProviderResponseError),
                 (dict(raw=b'not json'), pp.ProviderResponseError),
                 (dict(reply={'choices': []}), pp.ProviderResponseError)]
        for kwargs, error in cases:
            with stub(**kwargs) as model, self.assertRaises(error, msg=kwargs):
                pp.polish(TEXT, 'profile', env=self.env(model, QINGHE_POLISH_TIMEOUT='0.2'))

    def test_unreachable_server_falls_back_to_local(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = {'QINGHE_POLISH_PROVIDER': 'openai', 'QINGHE_POLISH_MODEL': 'm', 'QINGHE_POLISH_BASE_URL': f'http://127.0.0.1:{port}/v1'}
        result = pp.polish(TEXT, 'profile', env=env)
        self.assertEqual((result.provider, result.fallback_from), ('local', 'openai'))


class PolishApiTests(ApiFixture):
    def setUp(self):
        super().setUp()
        quiet = patch('sys.stderr')
        quiet.start()
        self.addCleanup(quiet.stop)

    def configure(self, model, **extra):
        os.environ.update({'QINGHE_POLISH_PROVIDER': 'openai', 'QINGHE_POLISH_MODEL': 'stub-model',
                           'QINGHE_POLISH_BASE_URL': model.url, **extra})

    def test_default_response_stays_compatible(self):
        self.login()
        status, result, _ = self.request('POST', '/api/ai/polish', dict(scene='profile', text=TEXT))
        self.assertEqual(status, 200)
        self.assertEqual({k: result[k] for k in ('engine', 'provider', 'model')}, dict(engine='local', provider='local', model=''))
        self.assertNotIn('fallbackFrom', result)

    def test_configured_model_is_reported_in_the_response(self):
        self.login()
        with stub(reply=openai_reply('我在苏州住了三年，每周六带大家散步。')) as model:
            self.configure(model)
            status, result, _ = self.request('POST', '/api/ai/polish', dict(scene='profile', text=TEXT, city='苏州'))
        self.assertEqual(status, 200)
        self.assertEqual(result, dict(text='我在苏州住了三年，每周六带大家散步。', engine='openai', provider='openai', model='stub-model'))

    def test_provider_errors_fall_back_or_return_clear_status(self):
        self.login()
        with stub(reply={'error': 'down'}, status=503) as model:
            self.configure(model)
            status, result, _ = self.request('POST', '/api/ai/polish', dict(scene='profile', text=TEXT))
            self.assertEqual((status, result['provider'], result['fallbackFrom']), (200, 'local', 'openai'))
            os.environ['QINGHE_POLISH_FALLBACK'] = 'off'
            status, result, _ = self.request('POST', '/api/ai/polish', dict(scene='profile', text=TEXT))
            self.assertEqual((status, result['message']), (502, 'AI 润色服务暂时不可用，请稍后再试'))
        self.assertEqual(self.request('POST', '/api/ai/polish', dict(scene='profile', text=TEXT), token='bad')[0], 401)

    def test_a_slow_model_does_not_block_other_requests(self):
        self.login()
        with stub(reply=openai_reply('我在苏州住了三年。')) as model:
            self.configure(model)
            model.release.clear()
            results = []
            worker = threading.Thread(target=lambda: results.append(self.request('POST', '/api/ai/polish', dict(scene='profile', text=TEXT))))
            worker.start()
            for _ in range(100):
                if model.requests:
                    break
                time.sleep(0.02)
            self.assertTrue(model.requests, 'polish request never reached the stub model')
            started = time.monotonic()
            self.assertEqual(self.request('GET', '/api/auth/me')[0], 200)
            self.assertLess(time.monotonic() - started, 2)
            model.release.set()
            worker.join(10)
        self.assertEqual((results[0][0], results[0][1]['provider']), (200, 'openai'))


NOTES = '我在成都长大，喜欢泡茶馆、吃苍蝇馆子，周末常去人民公园和玉林路。'


def draft_request(part='all'):
    return pp.DraftRequest(NOTES, '成都', ('美食探店', '城市漫步'), tuple(pp.package_plan(('half', 'full', 'evening'))), part, 0)


def valid_draft():
    def node(time, place, activity):
        return dict(time=time, place=place, activity=activity)
    return dict(
        bio='我在成都长大，周末会去人民公园喝茶，也会去玉林路吃饭。',
        highlights=['带你去泡老茶馆', '按你的口味去探店', '不赶路的城市漫步'],
        itineraries=dict(
            half=[node('10:00', '人民公园', '坐下来泡茶'), node('12:00', '玉林路', '尝尝本地吃食'), node('14:00', '沿途散步', '慢慢走一走')],
            full=[node('09:00', '人民公园', '坐下来泡茶'), node('13:00', '玉林路', '尝尝本地吃食'), node('17:00', '休息', '找个地方坐一会儿')],
            evening=[node('17:00', '人民公园', '坐下来泡茶'), node('18:30', '玉林路', '尝尝本地吃食'), node('20:00', '自由拍照', '看到喜欢的就停下来拍')],
        ))


class DraftParsingTests(ProviderTestCase):
    def test_parse_draft_accepts_json_and_fenced_json(self):
        request = draft_request()
        payload = valid_draft()
        self.assertEqual(pp.parse_draft(json.dumps(payload, ensure_ascii=False), request), payload)
        wrapped = '<think>先核对地点</think>\n```json\n' + json.dumps(payload, ensure_ascii=False) + '\n```'
        self.assertEqual(pp.parse_draft(wrapped, request)['itineraries']['half'][0]['place'], '人民公园')
        self.assertEqual(pp.parse_draft(payload, request)['highlights'], payload['highlights'])

    def test_parse_draft_rejects_missing_long_and_bad_times(self):
        request = draft_request()
        cases = []
        missing = valid_draft()
        del missing['bio']
        cases.append((missing, '缺少'))
        long_bio = valid_draft()
        long_bio['bio'] = '我' * 601
        cases.append((long_bio, '600'))
        long_highlight = valid_draft()
        long_highlight['highlights'] = ['城' * 21, '泡茶', '散步']
        cases.append((long_highlight, '20'))
        bad_time = valid_draft()
        bad_time['itineraries']['half'][0]['time'] = '下午两点'
        cases.append((bad_time, 'HH:MM'))
        short_trip = valid_draft()
        short_trip['itineraries']['evening'] = short_trip['itineraries']['evening'][:2]
        cases.append((short_trip, '3 到 5'))
        for payload, fragment in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaises(pp.ProviderResponseError) as caught:
                    pp.parse_draft(payload, request)
                self.assertIn(fragment, str(caught.exception))
        with self.assertRaises(pp.ProviderResponseError):
            pp.parse_draft('```json\n[1, 2, 3]\n```', request)
        with self.assertRaises(pp.ProviderResponseError):
            pp.parse_draft('这不是 JSON', request)

    def test_parse_draft_rejects_extra_unordered_and_invented_places(self):
        request = draft_request()
        extra = valid_draft()
        extra['price'] = 80
        invented = valid_draft()
        invented['itineraries']['half'][0]['place'] = '宽窄巷子'
        invented_activity = valid_draft()
        invented_activity['itineraries']['full'][1]['activity'] = '步行到宽窄巷子'
        extra_node = valid_draft()
        extra_node['itineraries']['half'][0]['note'] = '多出来的'
        unordered = valid_draft()
        unordered['itineraries']['half'][0]['time'] = '15:00'
        unordered['itineraries']['half'][1]['time'] = '11:00'
        too_long = valid_draft()
        too_long['itineraries']['half'] = [
            dict(time='09:00', place='人民公园', activity='坐下来泡茶'),
            dict(time='12:00', place='玉林路', activity='尝尝本地吃食'),
            dict(time='18:00', place='沿途散步', activity='慢慢走一走')]
        early_evening = valid_draft()
        early_evening['itineraries']['evening'] = [
            dict(time='14:00', place='人民公园', activity='坐下来泡茶'),
            dict(time='15:00', place='玉林路', activity='尝尝本地吃食'),
            dict(time='16:00', place='沿途散步', activity='慢慢走一走')]
        cases = [
            (extra, '多余'), (invented, '没有的地点'), (invented_activity, '没有的地点'),
            (extra_node, '节点'), (unordered, '递增'), (too_long, '套餐时长'), (early_evening, '17:00'),
        ]
        for payload, fragment in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaises(pp.ProviderResponseError) as caught:
                    pp.parse_draft(payload, request)
                self.assertIn(fragment, str(caught.exception))

    def test_teahouse_and_compound_names_must_come_from_the_notes(self):
        hidden = valid_draft()
        hidden['itineraries']['half'][1]['activity'] = '去鹤鸣茶社喝茶'
        with self.assertRaises(pp.ProviderResponseError) as caught:
            pp.parse_draft(hidden, draft_request())
        self.assertIn('没有的地点', str(caught.exception))
        taikoo = valid_draft()
        taikoo['itineraries']['evening'][1]['activity'] = '逛太古里'
        with self.assertRaises(pp.ProviderResponseError):
            pp.parse_draft(taikoo, draft_request())

        notes = NOTES + '也常去鹤鸣茶社。'
        request = pp.DraftRequest(notes, '成都', ('美食探店', '城市漫步'), tuple(pp.package_plan(('half', 'full', 'evening'))), 'all', 0)
        shown = valid_draft()
        shown['itineraries']['half'][1]['place'] = '鹤鸣茶社'
        shown['itineraries']['half'][1]['activity'] = '去鹤鸣茶社喝茶'
        parsed = pp.parse_draft(shown, request)
        self.assertEqual(parsed['itineraries']['half'][1]['place'], '鹤鸣茶社')
        self.assertEqual(parsed['itineraries']['half'][1]['activity'], '去鹤鸣茶社喝茶')
        ordinary = valid_draft()
        ordinary['itineraries']['full'][0]['activity'] = '回到酒店休息'
        ordinary['itineraries']['full'][1]['activity'] = '去朋友家里坐坐'
        ordinary['itineraries']['full'][2]['activity'] = '傍晚到夜里'
        self.assertEqual(pp.parse_draft(ordinary, draft_request())['itineraries']['full'][1]['activity'], '去朋友家里坐坐')

    def test_bad_provider_draft_falls_back_to_local(self):
        @pp.register('draft-broken')
        class Broken(pp.PolishProvider):
            def polish(self, request):
                return ''

            def draft(self, request):
                return '{"place": "宽窄巷子"}'
        self.addCleanup(pp.PROVIDERS.pop, 'draft-broken', None)
        env = {'QINGHE_POLISH_PROVIDER': 'draft-broken', 'QINGHE_POLISH_MODEL': 'stub'}
        result = pp.draft(NOTES, '成都', ('城市漫步',), env=env)
        self.assertEqual((result.provider, result.fallback_from), ('local', 'draft-broken'))
        for nodes in result.payload['itineraries'].values():
            for node in nodes:
                self.assertTrue(node['place'] in NOTES or node['place'] in pp.GENERIC_PLACES)
        with self.assertRaises(pp.ProviderResponseError) as caught:
            pp.draft(NOTES, '成都', env={**env, 'QINGHE_POLISH_FALLBACK': 'off'})
        self.assertEqual(caught.exception.status, 502)


class DraftProviderHttpTests(ProviderTestCase):
    def test_openai_draft_asks_for_json_only(self):
        with stub(reply=openai_reply(json.dumps(valid_draft(), ensure_ascii=False))) as model:
            env = {'QINGHE_POLISH_PROVIDER': 'openai', 'QINGHE_POLISH_MODEL': 'qwen2.5:7b',
                   'QINGHE_POLISH_BASE_URL': model.url, 'QINGHE_POLISH_API_KEY': 'sk-local-test',
                   'QINGHE_POLISH_FALLBACK': 'off'}
            result = pp.draft(NOTES, '成都', ('美食探店',), env=env)
        self.assertEqual((result.provider, result.model, result.payload['itineraries']['half'][0]['place']),
                         ('openai', 'qwen2.5:7b', '人民公园'))
        system = model.requests[0]['body']['messages'][0]['content']
        user = model.requests[0]['body']['messages'][1]['content']
        for rule in ('只输出一个 JSON', '不要新增具体店名', '17:00', '半日轻游'):
            self.assertIn(rule, system)
        self.assertIn(NOTES, user)
        self.assertEqual(model.requests[0]['headers']['authorization'], 'Bearer sk-local-test')

    def test_anthropic_draft_uses_the_same_prompt(self):
        reply = dict(content=[dict(type='text', text=json.dumps(valid_draft(), ensure_ascii=False))])
        with stub(reply=reply) as model:
            env = {'QINGHE_POLISH_PROVIDER': 'anthropic', 'QINGHE_POLISH_MODEL': 'claude-haiku-5-5',
                   'QINGHE_POLISH_BASE_URL': model.url, 'QINGHE_POLISH_API_KEY': 'sk-ant-test',
                   'QINGHE_POLISH_FALLBACK': 'off'}
            result = pp.draft(NOTES, '成都', env=env)
        self.assertEqual(result.provider, 'anthropic')
        sent = model.requests[0]
        self.assertEqual(sent['path'], '/v1/messages')
        self.assertEqual(sent['body']['max_tokens'], 2048)
        self.assertIn('只输出一个 JSON', sent['body']['system'])
        self.assertIn(NOTES, sent['body']['messages'][0]['content'])


class DraftApiTests(ApiFixture):
    def setUp(self):
        super().setUp()
        quiet = patch('sys.stderr')
        quiet.start()
        self.addCleanup(quiet.stop)

    def test_a_slow_draft_does_not_block_other_requests(self):
        self.login()
        with stub(reply=openai_reply(json.dumps(valid_draft(), ensure_ascii=False))) as model:
            os.environ.update({'QINGHE_POLISH_PROVIDER': 'openai', 'QINGHE_POLISH_MODEL': 'stub-model',
                               'QINGHE_POLISH_BASE_URL': model.url, 'QINGHE_POLISH_FALLBACK': 'off'})
            model.release.clear()
            results = []
            worker = threading.Thread(target=lambda: results.append(self.request(
                'POST', '/api/ai/profile-draft', dict(notes=NOTES, city='成都'))))
            worker.start()
            for _ in range(100):
                if model.requests:
                    break
                time.sleep(0.02)
            self.assertTrue(model.requests, 'draft request never reached the stub model')
            started = time.monotonic()
            self.assertEqual(self.request('GET', '/api/auth/me')[0], 200)
            self.assertLess(time.monotonic() - started, 2)
            model.release.set()
            worker.join(10)
        self.assertEqual((results[0][0], results[0][1]['provider']), (200, 'openai'))


if __name__ == '__main__':
    unittest.main()
