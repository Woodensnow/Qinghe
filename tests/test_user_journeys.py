"""Feature stories through real HTTP requests, with independent users and data.

Run: python -m unittest discover -s tests -p test_user_journeys.py -v
These scenarios exercise supported user workflows, not malformed requests.
"""
from datetime import date, datetime, timedelta, timezone
from itertools import count
from urllib.parse import urlencode
from unittest.mock import patch

from test_server import ApiFixture
import store


PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1sAAAAASUVORK5CYII='


class UserJourneys(ApiFixture):
    """Each test tells one story; helpers only shorten routine API operations."""

    def api(self, method, path, body=None, actor=None, expected=200):
        status, payload, _ = self.request(method, path, body, token=actor['token'] if actor else None)
        self.assertEqual(status, expected, f'{method} {path}: {payload}')
        return payload

    def join(self, name, email):
        return self.api('POST', '/api/auth/register',
                        dict(name=name, email=email, password='walkwithme123'), expected=201)

    def publish(self, owner, **changes):
        service = dict(name='阿禾向导', city='苏州', headline='小巷计划：喝咖啡逛老街的慢旅行',
                       bio='我在这座城市生活多年，熟悉老街和咖啡馆，愿意按照你的节奏一起慢慢走。',
                       price=200, services=['城市漫步', '美食探店'], languages=['中文', '英语'],
                       cover='/assets/images/guide-shanghai.jpg')
        service.update(changes)
        return self.api('POST', '/api/guides', service, owner, 201)['guide']

    def search(self, **filters):
        return self.api('GET', '/api/guides?' + urlencode(filters))['guides']

    def book(self, traveler, guide, package=0, days=14, people=2, **changes):
        request = dict(guideId=guide['id'], packageId=guide['packages'][package]['id'],
                       date=(date.today() + timedelta(days=days)).isoformat(), time='10:00',
                       people=people, note='不赶路，途中找一家咖啡馆。')
        request.update(changes)
        return self.api('POST', '/api/bookings', request, traveler, 201)['booking']

    def chat(self, traveler, guide, expected=201):
        return self.api('POST', '/api/conversations', {'guideId': guide['id']}, traveler, expected)['conversation']

    def send(self, actor, conversation, body):
        return self.api('POST', f'/api/conversations/{conversation["id"]}/messages',
                        {'body': body}, actor, 201)['message']

    def inbox(self, actor):
        return self.api('GET', '/api/conversations', actor=actor)['conversations']

    def unread(self, actor):
        return self.api('GET', '/api/messages/unread', actor=actor)['count']

    def test_first_weekend_from_discovery_to_meeting_arrangements(self):
        """周末第一次来苏州：筛选 → 详情 → 预约 → 与真人地陪约见。"""
        local = self.join('阿禾', 'local@example.cn')
        published = self.publish(local)
        traveler = self.join('周末旅人', 'weekend@example.cn')
        choices = self.search(city='苏州', service='城市漫步', language='英语', maxPrice=250, q='小巷计划')
        self.assertEqual([g['id'] for g in choices], [published['id']])
        detail = self.api('GET', '/api/guides/' + choices[0]['id'], actor=traveler)['guide']
        self.assertEqual(detail['name'], '阿禾向导')
        self.assertEqual(detail['packages'][0]['name'], '半日轻游')
        order = self.book(traveler, detail, note='两个人，想在平江路喝咖啡 ☕')
        self.assertEqual((order['total'], order['people'], order['status']), (200, 2, 'pending'))
        conversation = self.chat(traveler, detail)
        self.send(traveler, conversation, '我们从苏州站出发，可以在平江路见面吗？')
        self.send(local, conversation, '可以，10 点在街口见，我会拿一把绿色雨伞。')
        thread = self.api('GET', f'/api/conversations/{conversation["id"]}/messages', actor=traveler)
        self.assertEqual([m['senderRole'] for m in thread['messages']], ['traveler', 'guide'])
        self.assertIn('绿色雨伞', thread['messages'][-1]['body'])
        orders = self.api('GET', '/api/bookings/mine', actor=traveler)['bookings']
        self.assertEqual([b['id'] for b in orders], [order['id']])
        self.assertEqual(orders[0]['note'], '两个人，想在平江路喝咖啡 ☕')

    def test_find_a_bilingual_food_walk_without_losing_the_budget(self):
        """筛选有交集：便宜不等于符合语言、服务和城市要求。"""
        owner = self.join('路线主理人', 'routes@example.cn')
        cheap = self.publish(owner, name='中文慢游', price=150, languages=['中文'])
        match = self.publish(owner, name='双语食客', price=240)
        expensive = self.publish(owner, name='精致漫游', price=400)
        self.publish(owner, name='英语摄影', price=220, services=['拍照陪游'])
        self.publish(owner, name='杭州食客', city='杭州', price=220)
        results = self.search(q='小巷计划', city='苏州', language='英语', service='美食探店', minPrice=200, maxPrice=300)
        self.assertEqual([g['id'] for g in results], [match['id']])
        # 放宽预算后能比较更多路线，再切换排序。
        results = self.search(q='小巷计划', city='苏州', service='美食探店', sort='price-asc')
        self.assertEqual([g['id'] for g in results], [cheap['id'], match['id'], expensive['id']])
        descending = self.search(q='小巷计划', city='苏州', service='美食探店', sort='price-desc')
        self.assertEqual([g['id'] for g in descending], [expensive['id'], match['id'], cheap['id']])

    def test_a_cafe_keyword_can_be_searched_in_english(self):
        """外国朋友输入大写 COFFEE，也能找到混合语言介绍的路线。"""
        owner = self.join('咖啡向导', 'coffee@example.cn')
        route = self.publish(owner, headline='Coffee 小巷计划：一杯咖啡认识苏州')
        self.publish(owner, headline='小巷计划：只逛老街不喝咖啡')
        self.assertEqual([g['id'] for g in self.search(city='苏州', q='COFFEE')], [route['id']])

    def test_three_packages_and_the_friend_who_joins_at_the_last_minute(self):
        """半日、全天、傍晚三套餐 × 四人、第五人加入、八人聚会。"""
        owner = self.join('家庭向导', 'family-guide@example.cn')
        traveler = self.join('家庭旅行', 'family@example.cn')
        guide = self.publish(owner, price=200)
        # Explicit examples are independent of the implementation's formula.
        cases = [('半日轻游', 0, 4, 200), ('半日轻游', 0, 5, 260), ('半日轻游', 0, 8, 440),
                 ('全天深度游', 1, 4, 340), ('全天深度游', 1, 5, 400), ('全天深度游', 1, 8, 580),
                 ('傍晚轻陪游', 2, 4, 150), ('傍晚轻陪游', 2, 5, 210), ('傍晚轻陪游', 2, 8, 390)]
        for day, (name, package, people, expected_total) in enumerate(cases, 20):
            with self.subTest(package=name, people=people):
                order = self.book(traveler, guide, package, days=day, people=people)
                self.assertEqual((order['packageName'], order['total']), (name, expected_total))
        self.assertEqual(len(self.api('GET', '/api/bookings/mine', actor=traveler)['bookings']), 9)

    def test_rain_changes_the_plan_cancel_and_rebook_the_same_slot(self):
        """取消散步改订全天游：同一日期和时间可以重新预约，旧单保留。"""
        owner = self.join('雨天向导', 'rain-guide@example.cn')
        traveler = self.join('带伞旅人', 'rain@example.cn')
        guide = self.publish(owner)
        original = self.book(traveler, guide)
        cancelled = self.api('PATCH', f'/api/bookings/{original["id"]}/cancel', actor=traveler)['booking']
        replacement = self.book(traveler, guide, package=1, note='改成全天，雨停后再走老街。')
        self.assertEqual(cancelled['status'], 'cancelled')
        self.assertNotEqual(original['id'], replacement['id'])
        orders = {b['id']: b for b in self.api('GET', '/api/bookings/mine', actor=traveler)['bookings']}
        self.assertEqual(orders[original['id']]['status'], 'cancelled')
        self.assertEqual(orders[replacement['id']]['total'], 340)
        self.assertEqual((original['date'], original['time']), (replacement['date'], replacement['time']))

    def test_guide_takes_a_break_but_keeps_existing_trip_and_chat(self):
        """地陪暂停接单期间，已有预约和私聊仍然能继续。"""
        owner = self.join('休假向导', 'holiday-guide@example.cn')
        traveler = self.join('已约旅人', 'holiday@example.cn')
        guide = self.publish(owner)
        order = self.book(traveler, guide)
        conversation = self.chat(traveler, guide)
        self.api('PATCH', '/api/guides/' + guide['id'], {'status': 'paused'}, owner)
        self.assertEqual(self.search(city='苏州', q='小巷计划'), [])
        mine = self.api('GET', '/api/guides/mine', actor=owner)['guides']
        self.assertEqual((mine[0]['id'], mine[0]['status']), (guide['id'], 'paused'))
        self.send(owner, conversation, '我只是暂停新预约，你的行程照常。')
        thread = self.api('GET', f'/api/conversations/{conversation["id"]}/messages', actor=traveler)
        self.assertEqual(thread['messages'][-1]['body'], '我只是暂停新预约，你的行程照常。')
        self.assertEqual(self.api('GET', '/api/bookings/mine', actor=traveler)['bookings'][0]['id'], order['id'])
        self.api('PATCH', '/api/guides/' + guide['id'], {'status': 'published'}, owner)
        self.assertEqual([g['id'] for g in self.search(city='苏州', q='小巷计划')], [guide['id']])
        newcomer = self.join('新旅人', 'newcomer@example.cn')
        self.assertEqual(self.book(newcomer, guide, days=15)['total'], 200)

    def test_a_second_visit_to_the_chat_reopens_the_original_conversation(self):
        """从卡片、详情重复私聊，不应重复创建会话或欢迎语。"""
        traveler = self.join('回头旅人', 'return@example.cn')
        guide = self.api('GET', '/api/guides/g_linxiaoman')['guide']
        first = self.chat(traveler, guide)
        self.assertEqual(self.unread(traveler), 1)
        self.send(traveler, first, '上次没问完，这条路适合带爸妈吗？')
        second = self.chat(traveler, guide, expected=200)
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(len(self.inbox(traveler)), 1)
        thread = self.api('GET', f'/api/conversations/{first["id"]}/messages', actor=traveler)
        self.assertEqual(len(thread['messages']), 2)
        self.assertEqual(thread['messages'][1]['body'], '上次没问完，这条路适合带爸妈吗？')
        self.assertEqual(self.unread(traveler), 0)

    def test_one_guide_handles_two_travelers_without_mixing_their_plans(self):
        """一位地陪同时与亲子家庭和摄影旅人沟通，各自看到自己的计划。"""
        owner = self.join('忙碌向导', 'busy@example.cn')
        family = self.join('亲子家庭', 'parents@example.cn')
        photographer = self.join('摄影旅人', 'photo@example.cn')
        guide = self.publish(owner)
        family_chat, photo_chat = self.chat(family, guide), self.chat(photographer, guide)
        self.send(family, family_chat, '带着孩子，希望沿路有休息的地方。')
        self.send(photographer, photo_chat, '想在日落时拍河边，带了三脚架。')
        self.assertEqual(self.unread(owner), 2)
        self.assertEqual({c['otherName'] for c in self.inbox(owner)}, {'亲子家庭', '摄影旅人'})
        self.api('GET', f'/api/conversations/{family_chat["id"]}/messages', actor=owner)
        self.assertEqual(self.unread(owner), 1)
        self.send(owner, family_chat, '亲子路线有两家可以休息的咖啡馆。')
        self.send(owner, photo_chat, '日落路线留出半小时架相机。')
        for actor, conversation, expected in [(family, family_chat, '亲子路线'), (photographer, photo_chat, '日落路线')]:
            with self.subTest(traveler=actor['user']['name']):
                thread = self.api('GET', f'/api/conversations/{conversation["id"]}/messages', actor=actor)
                self.assertEqual(len(thread['messages']), 2)
                self.assertTrue(thread['messages'][-1]['body'].startswith(expected))
                self.assertEqual(len(self.inbox(actor)), 1)

    def test_inbox_moves_the_latest_reply_to_the_top_without_reading_it(self):
        """最新回复置顶；看会话列表不会清空未读，打开对应会话才会。"""
        owner = self.join('消息向导', 'inbox@example.cn')
        traveler = self.join('跨城旅人', 'two-cities@example.cn')
        suzhou = self.publish(owner, name='苏州向导')
        hangzhou = self.publish(owner, name='杭州向导', city='杭州')
        first, second = self.chat(traveler, suzhou), self.chat(traveler, hangzhou)
        ticks = count()
        origin = datetime.now(timezone.utc)
        # Only time is controlled: no sleeps or mocked business responses.
        def next_time():
            return (origin + timedelta(seconds=next(ticks))).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        with patch('server.now_iso', side_effect=next_time):
            self.send(owner, first, '苏州的第一条路线建议')
            self.send(owner, second, '杭州见面地点更新')
            self.send(owner, first, '苏州还有一家新开的咖啡馆')
        inbox = self.inbox(traveler)
        self.assertEqual([c['id'] for c in inbox], [first['id'], second['id']])
        self.assertEqual(inbox[0]['lastMessage'], '苏州还有一家新开的咖啡馆')
        self.assertEqual([c['unread'] for c in inbox], [2, 1])
        self.assertEqual(self.unread(traveler), 3)
        self.api('GET', f'/api/conversations/{first["id"]}/messages', actor=traveler)
        self.assertEqual(self.unread(traveler), 1)
        self.assertEqual([c['unread'] for c in self.inbox(traveler)], [0, 1])

    def test_new_avatar_reaches_existing_services_and_both_chat_views(self):
        """换头像和昵称后，已有服务及已有私聊显示新的个人形象。"""
        owner = self.join('头像向导', 'avatar-guide@example.cn')
        traveler = self.join('旧昵称', 'avatar-traveler@example.cn')
        guide = self.publish(owner)
        conversation = self.chat(traveler, guide)
        guide_avatar = self.api('POST', '/api/profile/photo', dict(kind='avatar', dataUrl=PNG), owner, 201)['url']
        traveler_avatar = self.api('POST', '/api/profile/photo', dict(kind='avatar', dataUrl=PNG), traveler, 201)['url']
        self.api('PATCH', '/api/profile', dict(name='带相机的小雨', city='上海', bio='喜欢自然的旅行照片。'), traveler)
        detail = self.api('GET', '/api/guides/' + guide['id'])['guide']
        self.assertEqual(detail['avatarUrl'], guide_avatar)
        self.assertEqual(self.inbox(traveler)[0]['otherAvatarUrl'], guide_avatar)
        provider_view = self.inbox(owner)[0]
        self.assertEqual((provider_view['otherName'], provider_view['otherAvatarUrl']), ('带相机的小雨', traveler_avatar))
        self.api('DELETE', '/api/profile/photo', {'kind': 'avatar'}, owner)
        self.assertEqual(self.api('GET', '/api/guides/' + guide['id'])['guide']['avatarUrl'], '')
        self.assertEqual(self.inbox(traveler)[0]['otherAvatarUrl'], '')

    def test_curate_a_photo_wall_keep_the_order_after_returning(self):
        """旅行照片墙：上传三张、删中间一张、再加入新照，重载后顺序不变。"""
        traveler = self.join('相册旅人', 'album@example.cn')
        photos = [self.api('POST', '/api/profile/photo', dict(kind='gallery', dataUrl=PNG), traveler, 201)['url'] for _ in range(3)]
        self.assertEqual(len(set(photos)), 3)
        self.api('DELETE', '/api/profile/photo', dict(kind='gallery', url=photos[1]), traveler)
        newest = self.api('POST', '/api/profile/photo', dict(kind='gallery', dataUrl=PNG), traveler, 201)['url']
        cover = self.api('POST', '/api/profile/photo', dict(kind='cover', dataUrl=PNG), traveler, 201)['url']
        # Discard the in-memory cache to exercise reading the saved JSON file.
        store._db = None
        profile = self.api('GET', '/api/auth/me', actor=traveler)['user']
        self.assertEqual(profile['photos'], [photos[0], photos[2], newest])
        self.assertEqual(profile['coverUrl'], cover)

    def test_polish_is_a_preview_until_the_traveler_accepts_it(self):
        """简介润色先预览，满意后才保存，事实信息仍在。"""
        traveler = self.join('文字旅人', 'words@example.cn')
        original = '我在苏州住了3年,每周六带大家散步,喜欢咖啡和老街'
        self.api('PATCH', '/api/profile', dict(name='文字旅人', city='苏州', bio=original), traveler)
        polished = self.api('POST', '/api/ai/polish', dict(scene='profile', text=original, city='苏州'), traveler)['text']
        self.assertNotEqual(polished, original)
        for fact in ('苏州', '3年', '每周六', '咖啡', '老街'):
            self.assertIn(fact, polished)
        self.assertEqual(self.api('GET', '/api/auth/me', actor=traveler)['user']['bio'], original)
        self.api('PATCH', '/api/profile', dict(name='文字旅人', city='苏州', bio=polished), traveler)
        self.assertEqual(self.api('GET', '/api/auth/me', actor=traveler)['user']['bio'], polished)

    def test_a_local_turns_their_own_photo_and_polished_intro_into_a_service(self):
        """从个人资料出发，上传自有封面、润色介绍，再发布第一条路线。"""
        owner = self.join('新地陪', 'first-route@example.cn')
        cover = self.api('POST', '/api/uploads', dict(kind='guide-cover', dataUrl=PNG), owner, 201)['url']
        intro = self.api('POST', '/api/ai/polish', dict(scene='guide', city='苏州',
                         text='我在苏州生活了5年,喜欢老街和咖啡,周末愿意带你慢慢逛,也能帮你拍照'), owner)['text']
        guide = self.publish(owner, cover=cover, bio=intro)
        detail = self.api('GET', '/api/guides/' + guide['id'])['guide']
        self.assertEqual((detail['cover'], detail['gallery'][0], detail['bio']), (cover, cover, intro))
        self.assertEqual(self.api('GET', '/api/guides/mine', actor=owner)['guides'][0]['id'], guide['id'])

    def test_two_trip_diaries_survive_sign_out_sign_in_and_storage_reload(self):
        """两位旅人退出再回来，各自的订单、留言和会话仍然对应自己的旅程。"""
        owner = self.join('行程向导', 'diary-guide@example.cn')
        first = self.join('小林', 'diary-one@example.cn')
        second = self.join('小陈', 'diary-two@example.cn')
        guide = self.publish(owner)
        orders = [self.book(first, guide, days=16, note='小林：想逛书店。'),
                  self.book(second, guide, days=17, note='小陈：想逛菜市场。')]
        chats = [self.chat(first, guide), self.chat(second, guide)]
        self.send(first, chats[0], '小林的书店行程')
        self.send(second, chats[1], '小陈的菜市场行程')
        for actor in (first, second):
            self.api('POST', '/api/auth/logout', actor=actor)
        store._db = None
        for email, expected_order, conversation, message in [('diary-one@example.cn', orders[0], chats[0], '小林的书店行程'),
                                                             ('diary-two@example.cn', orders[1], chats[1], '小陈的菜市场行程')]:
            with self.subTest(traveler=email):
                returned = self.api('POST', '/api/auth/login', dict(email=email, password='walkwithme123'))
                mine = self.api('GET', '/api/bookings/mine', actor=returned)['bookings']
                self.assertEqual([b['id'] for b in mine], [expected_order['id']])
                self.assertEqual(mine[0]['note'], expected_order['note'])
                self.assertEqual([c['id'] for c in self.inbox(returned)], [conversation['id']])
                thread = self.api('GET', f'/api/conversations/{conversation["id"]}/messages', actor=returned)
                self.assertEqual([m['body'] for m in thread['messages']], [message])

    def test_two_sentences_become_a_published_itinerary(self):
        """本地人写两句话，生成简介和行程，采用后详情里能看到每个套餐的时间线。"""
        owner = self.join('成阿禾', 'chengdu-guide@example.cn')
        notes = '我在成都长大，喜欢泡茶馆、吃苍蝇馆子，周末常去人民公园和玉林路。'
        draft = self.api('POST', '/api/ai/profile-draft', dict(
            notes=notes, city='成都', services=['美食探店', '城市漫步'], part='all'), owner)
        self.assertEqual(draft['provider'], 'local')
        self.assertEqual(len(draft['highlights']), 3)
        guide = self.publish(owner, name='成阿禾', city='成都', headline='人民公园喝茶，玉林路吃馆子',
                             bio=draft['bio'], services=['美食探店', '城市漫步'],
                             highlights=draft['highlights'], itineraries=draft['itineraries'])
        detail = self.api('GET', '/api/guides/' + guide['id'])['guide']
        self.assertEqual(detail['highlights'], draft['highlights'])
        self.assertEqual(detail['bio'], draft['bio'])
        self.assertEqual(len(detail['packages']), 3)
        for package in detail['packages']:
            self.assertEqual(package['itinerary'], draft['itineraries'][package['key']])
            self.assertGreaterEqual(len(package['itinerary']), 3)
            for node in package['itinerary']:
                self.assertTrue(node['place'] in notes or node['place'] in ('沿途散步', '自由拍照', '休息', '根据你的兴趣现场调整'))
