"""Matching profile APIs; PyTorch is loaded only for recommendations."""
from datetime import date, timedelta
import importlib.util
import math
import re
from auth_utils import make_id
from store import data, save, now_iso
from matching_data import INTERESTS, PACES
from matching_service import MODEL_PATH, rank_pairs, candidate


def handle(handler, path, query, check, public_guide, catalog):
    db, method = data(), handler.command
    db.setdefault('matchTrips', [])

    def selection(body, field, allowed):
        values = body.get(field, [])
        label = {'services': '服务类型', 'languages': '沟通语言', 'interests': '旅行兴趣', 'paces': '旅行节奏', 'weekdays': '接单星期'}[field]
        check(isinstance(values, list) and values and all(isinstance(v, (str, int)) and v in allowed for v in values), f'请至少选择一项有效的{label}')
        return list(dict.fromkeys(values))

    def day(value):
        check(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), '请选择有效日期')
        try:
            return date.fromisoformat(value)
        except ValueError:
            check(False, '请选择有效日期')

    def text(body, field, limit):
        return str(body.get(field) or '').strip()[:limit]

    if method == 'GET' and path == '/api/matching/meta':
        return 200, dict(interests=INTERESTS, paces=PACES, hasModel=MODEL_PATH.exists(),
                         hasTorch=importlib.util.find_spec('torch') is not None,
                         notice='教学模型使用合成偏好训练；推荐分不是接受概率。')
    user = handler.current_user()
    if path == '/api/matching/trip':
        trip = next((t for t in db['matchTrips'] if t['userId'] == user['id'] and t['status'] == 'open'), None)
        if method == 'GET':
            return 200, {'trip': trip}
        if method == 'DELETE':
            if trip:
                trip['status'] = 'closed'
                save()
            return 200, {'ok': True}
        if method == 'POST':
            body = handler.read_body()
            check(body.get('share') is True, '请确认向符合条件的地陪展示本次需求')
            city = text(body, 'city', 20)
            check(city in catalog['CITIES'], '请选择城市')
            requested_date = day(body.get('date'))
            check(date.today() <= requested_date <= date.today() + timedelta(days=180), '请选择未来 180 天内的日期')
            check(body.get('time') in catalog['TIME_SLOTS'], '请选择开始时间')
            people, budget, hours = body.get('people'), body.get('budget'), body.get('hours')
            check(type(people) is int and 1 <= people <= 8, '同行人数需要在 1–8 人之间')
            check(isinstance(budget, (int, float)) and math.isfinite(budget) and budget > 0, '请输入整团总预算')
            check(hours in (3, 4, 8), '请选择 3、4 或 8 小时套餐')
            values = dict(city=city, date=requested_date.isoformat(), time=body['time'], people=people,
                          budget=budget, hours=hours, services=selection(body, 'services', catalog['SERVICE_TYPES']),
                          languages=selection(body, 'languages', catalog['LANGUAGES']),
                          interests=selection(body, 'interests', INTERESTS), paces=selection(body, 'paces', PACES),
                          description=text(body, 'description', 300), updatedAt=now_iso())
            if trip:
                trip.update(values)
            else:
                trip = dict(id=make_id('trip'), userId=user['id'], status='open', **values)
                db['matchTrips'].append(trip)
            save()
            return 200, {'trip': trip}

    preference_match = re.fullmatch(r'/api/matching/preferences/([^/]+)', path)
    if method == 'PATCH' and preference_match:
        guide = next((g for g in db['guides'] if g['id'] == preference_match[1] and g.get('ownerId') == user['id']), None)
        check(guide, '请先选择自己发布的服务', status=404)
        body = handler.read_body()
        maximum = body.get('maxPeople')
        check(type(maximum) is int and 1 <= maximum <= 8, '接待人数需要在 1–8 人之间')
        blocked = body.get('blockedDates', [])
        check(isinstance(blocked, list) and len(blocked) <= 180, '休息日期最多填写 180 个')
        guide['matchPreferences'] = dict(maxPeople=maximum, weekdays=selection(body, 'weekdays', list(range(7))),
                           blockedDates=list(dict.fromkeys(day(value).isoformat() for value in blocked)),
                           interests=selection(body, 'interests', INTERESTS), paces=selection(body, 'paces', PACES),
                           text=text(body, 'text', 300))
        save()
        return 200, {'guide': public_guide(guide, user)}

    if method == 'POST' and path == '/api/matching/contact':
        body = handler.read_body()
        guide = next((g for g in db['guides'] if g['id'] == body.get('guideId') and g.get('ownerId') == user['id']), None)
        trip = next((t for t in db['matchTrips'] if t['id'] == body.get('tripId') and t['status'] == 'open'), None)
        check(guide and trip, '行程或服务不存在', status=404)
        offer, reason = candidate(trip, guide, db)
        check(offer, reason or '当前行程无法联系', status=409)
        conversation = next((c for c in db['conversations'] if c['guideId'] == guide['id'] and c['travelerId'] == trip['userId']), None)
        if not conversation:
            traveler = next(u for u in db['users'] if u['id'] == trip['userId'])
            now = now_iso()
            conversation = dict(id=make_id('c'), guideId=guide['id'], guideName=guide['name'], guideCover=guide['cover'],
                                guideCity=guide['city'], guideAvatarTone=guide['avatarTone'], guideAvatarUrl=guide.get('avatarUrl', ''),
                                guideOwnerId=user['id'], travelerId=traveler['id'], travelerName=traveler['name'],
                                travelerAvatarTone=traveler['avatarTone'], travelerAvatarUrl=traveler.get('avatarUrl', ''),
                                createdAt=now, updatedAt=now, unreadTraveler=0, unreadGuide=0)
            db['conversations'].append(conversation)
            save()
        return 200, {'conversationId': conversation['id']}

    if method == 'GET' and path in ('/api/matching/guides', '/api/matching/travelers'):
        check(importlib.util.find_spec('torch') is not None, '请用项目 .venv 启动，并安装 requirements-matching.txt', status=503)
        check(MODEL_PATH.exists(), '请先运行 tools/train_matching.py 训练教学模型', status=503)
        if path.endswith('/guides'):
            trip = next((t for t in db['matchTrips'] if t['userId'] == user['id'] and t['status'] == 'open'), None)
            check(trip, '请先填写行程需求', status=404)
            trips, guides = [trip], db['guides']
        else:
            guide_id = query.get('guideId', [''])[0]
            guide = next((g for g in db['guides'] if g['id'] == guide_id and g.get('ownerId') == user['id']), None)
            check(guide, '请选择自己发布的服务', status=404)
            trips, guides = [t for t in db['matchTrips'] if t['status'] == 'open'], [guide]
        result = rank_pairs(trips, guides, db)
        for match in result['matches']:
            guide = next(g for g in guides if g['id'] == match['guideId'])
            match['guide'] = public_guide(guide, user)
            if path.endswith('/travelers'):
                trip = next(t for t in trips if t['id'] == match['tripId'])
                traveler = next(u for u in db['users'] if u['id'] == trip['userId'])
                match['trip'] = {k: v for k, v in trip.items() if k != 'userId'}
                match['traveler'] = dict(name=traveler['name'], avatarUrl=traveler.get('avatarUrl', ''))
                conversation = next((c for c in db['conversations'] if c['guideId'] == guide['id'] and c['travelerId'] == traveler['id']), None)
                match['conversationId'] = conversation['id'] if conversation else None
        return 200, result
    check(False, '匹配接口不存在', status=404)
