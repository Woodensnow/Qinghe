"""Create local test accounts for checking two-sided matching in the browser.

Runs against a started server through the public API (register, publish a
guide service, fill match preferences, post a trip), so data goes through the
same validation as real users. Safe to re-run: existing accounts log in, and
their service, preferences and trip are updated instead of duplicated.

    .venv/bin/python tools/seed_matching_demo.py [--base http://127.0.0.1:4173]

Accounts (local testing only, all share TEST_PASSWORD):
    guide1@qinghe.test … guide4@qinghe.test        地陪，各发布一项上海服务
    traveler1@qinghe.test … traveler4@qinghe.test  旅人，各发布一个上海行程
`python main.py --reset` (server stopped) removes them, but it also clears ALL
other business data and uploads, restoring the original demo data.
"""
import argparse
from datetime import date, timedelta
import json
from urllib import request
from urllib.error import HTTPError

TEST_PASSWORD = 'qinghe-test-2026'
CITY = '上海'
COVER = '/assets/images/guide-shanghai.jpg'

GUIDES = [
    dict(email='guide1@qinghe.test', name='咖啡阿满', price=220, services=['城市漫步', '美食探店'],
         headline='带你喝遍梧桐区的小咖啡馆',
         bio='在上海住了十几年，周末最常做的事就是找新开的咖啡馆。可以带你从一杯手冲开始，再去弄堂里吃几家老字号的小吃，'
             '路线不赶，走累了就坐下来聊聊天。',
         interests=['咖啡', '美食'], paces=['慢慢逛'], text='欢迎喜欢咖啡和本地小吃、愿意慢慢走的朋友。'),
    dict(email='guide2@qinghe.test', name='老城讲古', price=260, services=['城市漫步', '接送陪同'],
         headline='一条街一条街讲老上海的来历',
         bio='做过几年文史讲解，熟悉外滩、老城厢和石库门的历史故事。每到一处都会讲讲建筑背后的人和事，'
             '时间安排张弛有度，适合想了解城市历史的朋友。',
         interests=['历史'], paces=['适中'], text='希望遇到对城市历史和老建筑感兴趣的旅人。'),
    dict(email='guide3@qinghe.test', name='镜头小周', price=300, services=['城市漫步', '拍照陪游'],
         headline='帮你拍下有光影的上海旅行照',
         bio='自由摄影师，熟悉滨江和公园里适合拍照的机位，也喜欢带大家去郊野看日落。行程会排得比较紧凑，'
             '赶在最好的光线出现前到达，帮你留下好看的照片。',
         interests=['摄影', '自然'], paces=['紧凑'], text='适合想多拍照、不怕多走路的朋友。'),
    dict(email='guide4@qinghe.test', name='亲子大熊', price=280, services=['城市漫步', '亲子出行', '周边包车'],
         headline='带一家人轻松玩转上海',
         bio='两个孩子的爸爸，知道带娃出门最需要什么。路线会留出休息和吃饭的时间，可以包车去周边的公园和农场，'
             '让大人孩子都玩得开心。',
         interests=['亲子', '自然'], paces=['慢慢逛'], text='欢迎带孩子出行的家庭，节奏慢一点没关系。'),
]

TRAVELERS = [
    dict(email='traveler1@qinghe.test', name='咖啡旅人', people=2, interests=['咖啡', '美食'], paces=['慢慢逛'],
         services=['城市漫步'], description='想找几家安静的咖啡馆坐坐，顺便尝尝本地小吃，不想赶路。'),
    dict(email='traveler2@qinghe.test', name='历史迷', people=1, interests=['历史'], paces=['适中'],
         services=['城市漫步'], description='第一次来上海，想听听外滩和老城厢背后的历史故事。'),
    dict(email='traveler3@qinghe.test', name='摄影爱好者', people=2, interests=['摄影', '自然'], paces=['紧凑'],
         services=['城市漫步', '拍照陪游'], description='带了相机，想多拍些风景和街景，行程可以紧凑一点。'),
    dict(email='traveler4@qinghe.test', name='带娃家庭', people=3, interests=['亲子'], paces=['慢慢逛'],
         services=['城市漫步', '亲子出行'], description='一家三口，孩子五岁，希望行程轻松，中间能休息。'),
]


class Client:
    def __init__(self, base):
        self.base, self.token = base.rstrip('/'), None

    def call(self, method, path, body=None):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        data = None if body is None else json.dumps(body).encode()
        try:
            with request.urlopen(request.Request(self.base + path, data, headers, method=method)) as response:
                return response.status, json.loads(response.read() or b'{}')
        except HTTPError as error:
            return error.code, json.loads(error.read() or b'{}')

    def sign_in(self, email, name):
        status, result = self.call('POST', '/api/auth/register', dict(email=email, password=TEST_PASSWORD, name=name))
        if status == 409:
            status, result = self.call('POST', '/api/auth/login', dict(email=email, password=TEST_PASSWORD))
        if status not in (200, 201):
            raise SystemExit(f'{email} 登录失败：{result}')
        self.token = result['token']
        return 'created' if status == 201 else 'existing'


def ok(status, result, what):
    if status not in (200, 201):
        raise SystemExit(f'{what}失败（{status}）：{result}')
    return result


def seed_guide(base, spec):
    client = Client(base)
    account = client.sign_in(spec['email'], spec['name'])
    mine = ok(*client.call('GET', '/api/guides/mine'), '读取服务')['guides']
    guide = next((g for g in mine if g['city'] == CITY), None)
    if guide is None:
        body = dict(name=spec['name'], city=CITY, headline=spec['headline'], bio=spec['bio'], price=spec['price'],
                    cover=COVER, services=spec['services'], languages=['中文', '英语'])
        guide = ok(*client.call('POST', '/api/guides', body), '发布服务')['guide']
    preferences = dict(maxPeople=6, weekdays=list(range(7)), blockedDates=[], interests=spec['interests'],
                       paces=spec['paces'], text=spec['text'])
    ok(*client.call('PATCH', f"/api/matching/preferences/{guide['id']}", preferences), '填写偏好')
    return client, guide, account


def seed_traveler(base, spec, trip_date):
    client = Client(base)
    account = client.sign_in(spec['email'], spec['name'])
    body = dict(share=True, city=CITY, date=trip_date, time='10:00', people=spec['people'], budget=800, hours=4,
                services=spec['services'], languages=['中文'], interests=spec['interests'], paces=spec['paces'],
                description=spec['description'])
    ok(*client.call('POST', '/api/matching/trip', body), '发布行程')
    return client, account


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', default='http://127.0.0.1:4173')
    args = parser.parse_args()
    trip_date = (date.today() + timedelta(days=3)).isoformat()
    guides = [(spec, *seed_guide(args.base, spec)) for spec in GUIDES]
    travelers = [(spec, *seed_traveler(args.base, spec, trip_date)) for spec in TRAVELERS]
    for spec, _, guide, account in guides:
        print(f"地陪 {spec['email']}（{account}）：{guide['name']}，偏好 {'、'.join(spec['interests'])} · {spec['paces'][0]}")
    for spec, _, account in travelers:
        print(f"旅人 {spec['email']}（{account}）：{CITY} {trip_date}，兴趣 {'、'.join(spec['interests'])} · {spec['paces'][0]}")
    print('\n旅人一侧：每位旅人的推荐地陪（按综合分）')
    for spec, client, _ in travelers:
        result = ok(*client.call('GET', '/api/matching/guides'), '获取推荐')
        ranked = [f"{m['guide']['name']} {m['score']}" for m in result['matches']]
        print(f"  {spec['name']}：{' > '.join(ranked) or '无'}  排除：{result['excluded']}")
    print('\n地陪一侧：每位地陪的推荐旅人（按综合分）')
    for spec, client, guide, _ in guides:
        result = ok(*client.call('GET', f"/api/matching/travelers?guideId={guide['id']}"), '获取推荐')
        ranked = [f"{m['traveler']['name']} {m['score']}" for m in result['matches']]
        print(f"  {guide['name']}：{' > '.join(ranked) or '无'}")


if __name__ == '__main__':
    main()
