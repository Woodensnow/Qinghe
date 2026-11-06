"""Local punctuation and expression polishing; no remote model required."""
import re

LIMITS = {'guide': 600, 'profile': 160}


def polish_text(text, context='profile', city='', variant=0):
    value = re.sub(r'\r\n?', '\n', text).strip()
    value = re.sub(r'[ \t]+', ' ', value)
    for old, new in zip(', . ? ! ; :'.split(), '，。？！；：'):
        value = re.sub(r'([\u4e00-\u9fff])\s*' + re.escape(old) + r'\s*', r'\1' + new, value)
    value = re.sub(r'[，,]\s*[，,]+', '，', value)
    value = re.sub(r'([。！？!?])\s*[。！？!?]+', r'\1', value)
    value = re.sub(r'^[，。；：、\s]+', '', value)
    for old, new in [('啥', '什么'), ('贼', '非常'), ('超级', '格外'), ('非常非常', '非常'), ('很多很多', '很多'), ('很好玩', '很有意思')]:
        value = value.replace(old, new)
    value = re.sub(r'挺(好|不错)', r'很\1', value)
    value = re.sub(r'(^|[。！？\n])\s*(嗯|然后|就是|其实|那个|反正|怎么说呢)[，,、\s]+', r'\1', value)
    value = re.sub(r'([\u4e00-\u9fff])喜欢', lambda m: m[0] if m[1] in '我你他她它也更最很挺特别' else m[1] + '，喜欢', value)
    value = re.sub(r'([\u4e00-\u9fff])(想|希望|期待)', lambda m: m[0] if m[1] in '我你他她它也更最很挺不没' else m[1] + '，' + m[2], value)
    value = re.sub(r'([\u4e00-\u9fff])(?=不去|不赶|不逛|不吃|不买)', lambda m: m[0] if m[1] in '我你他她它也更最很挺' else m[1] + '，', value)
    value = re.sub(r'(喝茶|吃饭|逛街|散步|拍照|看书|喝咖啡|逛小巷)(?=逛|走|吃|喝|看|拍|买)', r'\1、', value)
    value = re.sub(r'咖啡(?=旧书店|书店)', '咖啡、', value)
    value = re.sub(r'喜欢([^，。！？\n]{1,20}?)喜欢', r'喜欢\1，也喜欢', value)
    value = re.sub(r'喜欢([^，。！？\n]{1,20}?)(想|希望|期待)', r'喜欢\1，\2', value)
    count = 0
    def preference(match):
        nonlocal count
        count += 1
        return '享受' if count % 3 == 0 else '喜欢'
    value = re.sub('喜欢', preference, value)
    def finish(line):
        line = line.strip()
        return line if not line or line[-1] in '。！？…' else line + '。'
    value = re.sub(r'\n{3,}', '\n\n', '\n'.join(finish(line) for line in value.split('\n')))
    if not value:
        return ''
    index = abs(int(variant)) % 3
    if context == 'guide':
        sentences = [s.strip() for s in re.split(r'(?<=[。！？!?])|\n+', value) if s.strip()]
        if '\n\n' not in value and len(sentences) >= 4:
            middle = (len(sentences) + 1) // 2
            value = ''.join(sentences[:middle]) + '\n\n' + ''.join(sentences[middle:])
        place = city if city and city != '全国' else '这座城'
        openings = [f'你好，我是生活在{place}的本地搭子。', f'我是{place}本地人，也是你在这座城市的临时朋友。', '你好，很高兴以本地人的身份认识你。']
        closings = ['如果你也喜欢这样的旅行方式，欢迎和我聊聊。', f'期待带你去看一个更日常、更松弛的{place}。', '路线可以一起商量，重要的是把时间花在喜欢的地方。']
        if not re.match(r'你好|大家好|hi|hello|我是', value, re.I):
            value = openings[index] + '\n\n' + value
        if not re.search('欢迎|期待|聊聊|联系|私聊|希望', value) and len(value) < 520:
            value += '\n\n' + closings[(index + 1) % 3]
    elif len(value) < 105 and not re.search('希望|期待|欢迎|聊聊|遇见', value):
        value += '\n\n' + ['希望在这里遇见同样热爱生活的人。', '如果你也喜欢这样的节奏，也许我们可以聊聊。', '期待把日常里的小发现，分享给同样好奇的你。'][index]
    return clip_text(value, LIMITS.get(context, LIMITS['profile']))


def clip_text(value, limit):
    """Cut to limit characters, preferring to end on a full sentence."""
    if len(value) <= limit:
        return value
    value = value[:limit]
    cut = max(value.rfind(c) for c in '。！？')
    return value[:cut + 1] if cut >= int(limit * .55) else value[:limit - 1].rstrip('，、；： \n') + '。'
