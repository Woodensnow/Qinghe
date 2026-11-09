"""Rule-based profile drafts for offline demos.

Itinerary places come only from the guide's own notes. Gaps are generic
nodes such as 沿途散步, never venues the guide did not write.
"""
import re

from ai_polish import polish_text

PACKAGE_KEYS = ('half', 'full', 'evening')
PACKAGES = (
    dict(key='half', name='半日轻游', duration='4 小时', hours=4, start=10 * 60),
    dict(key='full', name='全天深度游', duration='8 小时', hours=8, start=9 * 60),
    dict(key='evening', name='傍晚轻陪游', duration='3 小时', hours=3, start=17 * 60),
)
GENERIC_PLACES = frozenset({'沿途散步', '自由拍照', '休息', '根据你的兴趣现场调整'})
FILLERS = (
    ('沿途散步', '慢慢走一走'),
    ('自由拍照', '看到喜欢的就停下来拍'),
    ('根据你的兴趣现场调整', '剩下的时间按你的兴趣安排'),
    ('休息', '找个地方坐一会儿'),
)
KEYWORDS = (
    ('茶', '带你去泡老茶馆'),
    ('咖啡', '找一家咖啡馆坐坐'),
    ('美食', '带你吃地道小吃'),
    ('夜景', '去看城市的夜景'),
    ('拍照', '沿途帮你拍照'),
    ('博物馆', '一起慢慢逛博物馆'),
    ('徒步', '不赶路地走一走'),
    ('小巷', '穿进附近的小巷'),
)
SERVICE_LINES = {
    '城市漫步': '不赶路的城市漫步',
    '美食探店': '按你的口味去探店',
    '接送陪同': '出发和返程我来陪',
    '拍照陪游': '帮你拍下沿途风景',
    '亲子出行': '适合慢慢走的亲子行',
    '周边包车': '周边一天我来安排',
}
FALLBACK_HIGHLIGHTS = ('按你的节奏慢慢逛', '出发前先聊清楚', '随时可以调整路线')
# Longer endings come first. Single-character tails catch 太古里 / 鹤鸣茶社 / 宽窄巷子里的园、楼、桥.
PLACE_SUFFIXES = (
    '风景区', '景区', '古镇', '古城', '茶社', '茶楼', '茶馆', '咖啡馆', '餐厅', '饭店', '饭馆',
    '酒吧', '酒馆', '广场', '公园', '乐园', '市场', '夜市', '街道', '大街', '街区', '巷子', '商圈',
    '路', '街', '巷', '寺', '馆', '庙', '山', '湖', '河', '湾', '桥', '塔', '楼', '店', '园', '里',
)
PLACE_SUFFIX = '(?:' + '|'.join(PLACE_SUFFIXES) + ')'
SPAN = re.compile(r'(?:去|在|逛|到)([^，。！？\n]{1,40})')
PLACE_IN_SPAN = re.compile(r'[\u4e00-\u9fff]{1,8}' + PLACE_SUFFIX)
PLACE_MENTION = re.compile(r'[\u4e00-\u9fff]{2,8}' + PLACE_SUFFIX)
CONNECTOR = re.compile(r'和|与|以及|还有|、')
# Longer words first so 回到 is consumed before a single 到.
_LEADING_WORDS = (
    '一会儿', '一会', '回到', '回去', '附近', '傍晚', '晚上', '下午', '上午',
    '中午', '早上', '早晨', '凌晨', '然后', '接着', '最后', '我们', '一起',
    '可以', '准备', '开始',
    '去', '在', '逛', '到', '了', '的', '过', '从', '沿', '来', '想', '常', '爱',
    '把', '往', '向', '就', '再', '又', '也', '还', '先',
)
LEADING_PLACE = re.compile('^(?:' + '|'.join(_LEADING_WORDS) + ')+')
TRAILING_PLACE = re.compile(r'(?:里|内|中|上|边|附近)$')
NOT_VENUES = frozenset({
    '这里', '那里', '哪里', '里面', '心里', '夜里', '下楼', '上楼',
    '赶路', '走路', '沿路', '一路',
})


def package_plan(keys, variant=0):
    """Canonical packages, with the half-day window shifting on alternate variants."""
    by_key = {package['key']: package for package in PACKAGES}
    plans = []
    for key in keys:
        base = by_key[key]
        start = 13 * 60 if key == 'half' and int(variant) % 2 else base['start']
        plans.append(dict(base, start=start))
    return plans


def extract_places(notes):
    """Places after 去/在/逛/到 that end with a venue suffix, in first-seen order."""
    found = []
    for span in SPAN.findall(notes or ''):
        for piece in CONNECTOR.split(span):
            piece = re.sub(r'^(?:了|的|过)+', '', piece.strip())
            match = PLACE_IN_SPAN.search(piece)
            if not match:
                continue
            name = re.sub(r'^(?:了|的|过)+', '', match.group(0))
            if len(name) >= 2 and name in notes and name not in found:
                found.append(name)
    return found


def _matched_suffix(name):
    for suffix in PLACE_SUFFIXES:
        if name.endswith(suffix):
            return suffix
    return ''


def _ends_with_suffix(name):
    return bool(_matched_suffix(name))


def _tighten_place(name):
    """Drop a run of leading verbs and a trailing 里/附近 when a real venue ending remains."""
    name = LEADING_PLACE.sub('', name)
    stem = TRAILING_PLACE.sub('', name)
    if stem != name and _ends_with_suffix(stem):
        name = stem
    return name


def mentioned_places(text):
    """Venue-like names inside a sentence. Ordinary words such as 不赶路 and 这里 are ignored.

    A one-character ending (里、店、楼、园) only counts when at least two characters
    sit in front of it, so 酒店 and 夜里 are not places. 家里 is "at home", not a venue.
    """
    names = []
    for raw in PLACE_MENTION.findall(text or ''):
        if '不赶' in raw:
            continue
        name = _tighten_place(raw)
        suffix = _matched_suffix(name)
        if (not suffix or len(name) < 2 or name in NOT_VENUES or name.endswith('家里')
                or (len(suffix) == 1 and len(name) - len(suffix) < 2)):
            continue
        if name not in names:
            names.append(name)
    return names


def build_highlights(notes, services, variant):
    lines = []
    for word, line in KEYWORDS:
        if word in notes and line not in lines:
            lines.append(line)
    for service in services or ():
        line = SERVICE_LINES.get(service)
        if line and line not in lines:
            lines.append(line)
    for line in FALLBACK_HIGHLIGHTS:
        if line not in lines:
            lines.append(line)
    start = int(variant) % len(lines)
    ordered = lines[start:] + lines[:start]
    return ordered[:3]


def activity_for(notes, index, variant):
    options = []
    if '茶' in notes:
        options.append('坐下来泡茶')
    if any(word in notes for word in ('吃', '美食', '馆子', '菜')):
        options.append('尝尝你提到的吃食')
    if '咖啡' in notes:
        options.append('喝一杯咖啡')
    if any(word in notes for word in ('拍照', '摄影')):
        options.append('停下来拍照')
    if '博物馆' in notes:
        options.append('慢慢看展')
    options.append('按你的节奏慢慢逛')
    return options[(index + int(variant)) % len(options)]


def choose_count(place_count, variant):
    count = 3 + (int(variant) % 3)
    if place_count > 5:
        return 5
    if place_count > count:
        return place_count
    return count


def _quarter_hour(minute):
    """Nearest 15-minute mark. Halves round away from the earlier mark."""
    # Add the half-step before dividing. int(minute) first would turn 7.5 into 7,
    # and 7 + 7 then falls short of the next quarter hour.
    return int((minute + 7.5) // 15) * 15


def spread_times(start, hours, count):
    """Quarter-hour stops. The last one starts at least 30 minutes before the package ends."""
    if count <= 1:
        return [start]
    latest = start + hours * 60 - 30
    span = latest - start
    times = [_quarter_hour(start + span * index / (count - 1)) for index in range(count)]
    times[0] = start
    for index in range(1, count):
        if times[index] <= times[index - 1]:
            times[index] = times[index - 1] + 15
    if times[-1] > latest:
        times = [minute - (times[-1] - latest) for minute in times]
    return times


def format_time(minute):
    return f'{minute // 60:02d}:{minute % 60:02d}'


def build_itinerary(notes, package, variant):
    places = extract_places(notes)
    if places:
        shift = int(variant) % len(places)
        places = places[shift:] + places[:shift]
    count = choose_count(len(places), variant)
    fillers = FILLERS[int(variant) % len(FILLERS):] + FILLERS[:int(variant) % len(FILLERS)]
    slots = [('place', place) for place in places[:count]]
    filler_index = 0
    while len(slots) < count:
        slots.append(('fill', fillers[filler_index % len(fillers)]))
        filler_index += 1
    nodes = []
    for (kind, value), minute in zip(slots, spread_times(package['start'], package['hours'], count)):
        if kind == 'place':
            place, activity = value, activity_for(notes, len(nodes), variant)
        else:
            place, activity = value
        nodes.append(dict(time=format_time(minute), place=place, activity=activity))
    return nodes


def draft_profile(notes, city='', services=(), packages=None, part='all', variant=0):
    """Build the requested block. `packages` are planned dicts; None selects all three."""
    plans = list(packages) if packages is not None else package_plan(PACKAGE_KEYS, variant)
    result = {}
    if part in ('all', 'bio'):
        bio = polish_text(notes, 'guide', city, variant).strip()
        if len(bio) < 20:
            place = city if city and city != '全国' else '这座城市'
            bio = f'你好，我是生活在{place}的本地人。想按你的节奏，把日常里的小地方慢慢走给你看。'
        result['bio'] = bio
    if part in ('all', 'highlights'):
        result['highlights'] = build_highlights(notes, services, variant)
    if part in ('all', 'itinerary'):
        result['itineraries'] = {package['key']: build_itinerary(notes, package, variant) for package in plans}
    return result
