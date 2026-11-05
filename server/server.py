"""Qinghe HTTP API and SPA host, using Python 3.10+ standard library only."""
import base64
import json
import math
import mimetypes
import os
import random
import re
import signal
import sys
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from auth_utils import hash_password, verify_password, make_id, make_token
from ai_polish import polish_text
from pricing import quote
from store import data, save, LOCK, ROOT, now_iso

PUBLIC = ROOT.parent / 'public'
UPLOADS = PUBLIC / 'uploads'
PID_FILE = ROOT / 'server.pid'
CATALOG = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
ACTIVE = {'pending', 'confirmed'}


class ApiError(Exception):
    def __init__(self, status, message, field=None):
        self.status, self.message, self.field = status, message, field


def check(condition, message, field=None, status=400):
    if not condition:
        raise ApiError(status, message, field)


def text(value, limit=1000):
    return str(value if value is not None else '').strip()[:limit]


def number(value, default=0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def find(items, **values):
    return next((item for item in items if all(item.get(k) == v for k, v in values.items())), None)


def public_user(user):
    return {k: user.get(k, [] if k == 'photos' else 'sage' if k == 'avatarTone' else '')
            for k in ('id', 'name', 'email', 'city', 'avatarTone', 'avatarUrl', 'coverUrl', 'bio', 'photos', 'joinedAt')}


def public_guide(guide, user=None):
    result = {k: v for k, v in guide.items() if k != 'ownerId'}
    result['isOwner'] = bool(user and guide.get('ownerId') == user['id'])
    return result


def create_session(user_id):
    token = make_token()
    db = data()
    db['sessions'] = [s for s in db['sessions'] if s['expiresAt'] > now_iso()]
    db['sessions'].append(dict(token=token, userId=user_id, createdAt=now_iso(),
                               expiresAt=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(timespec='milliseconds').replace('+00:00', 'Z')))
    save()
    return token


def role_of(conversation, user_id):
    if conversation['travelerId'] == user_id:
        return 'traveler'
    if conversation.get('guideOwnerId') == user_id:
        return 'guide'
    return None


def conversation_view(conversation, user_id):
    db = data()
    role = role_of(conversation, user_id)
    messages = [m for m in db['messages'] if m['conversationId'] == conversation['id']]
    guide = find(db['guides'], id=conversation['guideId']) or {}
    traveler = find(db['users'], id=conversation['travelerId']) or {}
    is_traveler = role == 'traveler'
    other = guide if is_traveler else traveler
    prefix = 'guide' if is_traveler else 'traveler'
    result = {k: conversation[k] for k in ('id', 'guideId', 'createdAt', 'updatedAt')}
    result.update({k: guide.get(source) or conversation.get(k, '')
                   for k, source in [('guideName', 'name'), ('guideCover', 'cover'), ('guideCity', 'city')]})
    result.update(role=role, otherRoleLabel='地陪' if is_traveler else '旅人',
                  otherName=other.get('name') or conversation.get(prefix + 'Name', ''),
                  otherAvatarTone=other.get('avatarTone') or conversation.get(prefix + 'AvatarTone') or 'sage',
                  otherAvatarUrl=other.get('avatarUrl') or conversation.get(prefix + 'AvatarUrl') or '',
                  unread=conversation.get('unreadTraveler' if is_traveler else 'unreadGuide', 0),
                  lastMessage=messages[-1]['body'] if messages else '',
                  lastMessageAt=messages[-1]['createdAt'] if messages else conversation['updatedAt'])
    return result


def upload_image(value):
    check(isinstance(value, str), '请选择一张本地图片', 'photo')
    match = re.fullmatch(r'data:image/(?:jpeg|jpg|png|webp);base64,([A-Za-z0-9+/=]+)', value)
    check(match, '仅支持 JPG、PNG 或 WebP 图片', 'photo')
    try:
        content = base64.b64decode(match[1], validate=True)
    except ValueError:
        raise ApiError(400, '图片读取失败，请重新选择', 'photo')
    check(content, '图片内容为空', 'photo')
    check(len(content) <= 5 * 1024 * 1024, '图片不能超过 5MB', 'photo')
    extension = ('jpg' if content.startswith(b'\xff\xd8\xff') else
                 'png' if content.startswith(b'\x89PNG\r\n\x1a\n') else
                 'webp' if len(content) >= 12 and content[:4] == b'RIFF' and content[8:12] == b'WEBP' else None)
    check(extension, '图片格式不正确，请重新选择', 'photo')
    UPLOADS.mkdir(exist_ok=True)
    filename = make_id('img') + '.' + extension
    (UPLOADS / filename).write_bytes(content)
    return '/uploads/' + filename


def remove_image(url):
    if isinstance(url, str) and re.fullmatch(r'/uploads/[A-Za-z0-9._-]+', url):
        target = UPLOADS / url.rsplit('/', 1)[-1]
        if target.is_file():
            target.unlink()


def sync_avatar(user):
    for guide in data()['guides']:
        if guide.get('ownerId') == user['id']:
            guide['avatarUrl'] = user['avatarUrl']


def usable_cover(cover):
    return any(c['value'] == cover for c in CATALOG['COVER_PRESETS']) or bool(
        re.fullmatch(r'/uploads/[A-Za-z0-9._-]+', cover) and (UPLOADS / cover.rsplit('/', 1)[-1]).is_file())


def make_packages(city, price):
    return [dict(id=make_id('pkg'), name=name, duration=duration, price=cost, description=description, includes=includes)
            for name, duration, cost, description, includes in [
                ('半日轻游', '4 小时', price, f'用半天时间，走一条不赶路的{city}本地路线。', ['一对一路线定制', '沿途讲解', '本地生活建议']),
                ('全天深度游', '8 小时', max(80, math.floor(price * 1.7 / 10 + .5) * 10), f'从早到晚慢慢逛，把{city}的日常与风景一次收进旅程。', ['全天行程定制', '路线陪同', '餐饮与交通建议']),
                ('傍晚轻陪游', '3 小时', max(60, math.floor(price * .75 / 10 + .5) * 10), '下班后的城市散步，适合差旅途中偷得半日闲。', ['夜间路线', '拍照协助', '本地宵夜推荐'])]]


class Handler(BaseHTTPRequestHandler):
    server_version = 'QinghePython/2.0'

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def respond(self, status, payload, content_type='application/json; charset=utf-8', cache='no-store'):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode() if isinstance(payload, (dict, list)) else payload
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', cache)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'")
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def read_body(self):
        check(not self.headers.get('Transfer-Encoding'), '请求格式不正确')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ApiError(400, '请求格式不正确')
        check(0 <= length <= 8 * 1024 * 1024, '请求内容过大')
        try:
            raw = self.rfile.read(length)
            check(len(raw) == length, '请求内容不完整')
            body = json.loads(raw) if raw else {}
        except (ValueError, UnicodeError):
            raise ApiError(400, '请求格式不正确')
        check(isinstance(body, dict), '请求格式不正确')
        return body

    def current_user(self, required=True):
        db = data()
        token = self.headers.get('Authorization', '').removeprefix('Bearer ').strip() if self.headers.get('Authorization', '').startswith('Bearer ') else ''
        session = find(db['sessions'], token=token)
        user = None
        if session:
            try:
                valid = datetime.fromisoformat(session['expiresAt'].replace('Z', '+00:00')) > datetime.now(timezone.utc)
            except (ValueError, TypeError):
                valid = False
            if valid:
                user = find(db['users'], id=session['userId'])
            else:
                db['sessions'].remove(session)
                save()
        if required:
            check(user, '请先登录', status=401)
        return user

    def dispatch(self):
        try:
            url = urlsplit(self.path)
            if url.path.startswith('/api/'):
                # A complete read/modify/save cycle is serialized, matching the old
                # single-process store and preventing lost updates between requests.
                with LOCK:
                    status, payload = self.api(url.path, parse_qs(url.query))
                self.respond(status, payload)
            else:
                check(self.command in ('GET', 'HEAD'), '请求方式不支持', status=405)
                self.static(url.path)
        except ApiError as error:
            payload = {'message': error.message}
            if error.field:
                payload['field'] = error.field
            self.respond(error.status, payload)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            self.log_error('Request failed: %s', error)
            self.respond(500, {'message': '请求处理失败'})

    do_GET = do_POST = do_PATCH = do_DELETE = do_HEAD = do_PUT = do_OPTIONS = dispatch

    def static(self, path):
        try:
            decoded = unquote(path, errors='strict')
            check('\x00' not in decoded, '路径格式不正确')
            target = (PUBLIC / decoded.lstrip('/')).resolve()
            check(target.is_relative_to(PUBLIC.resolve()), '无权访问', status=403)
        except (ValueError, UnicodeError):
            raise ApiError(400, '路径格式不正确')
        if not target.is_file():
            if Path(decoded).suffix:
                return self.respond(404, b'Not found', 'text/plain; charset=utf-8')
            target = PUBLIC / 'index.html'
        mime = {'.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.svg': 'image/svg+xml'}.get(target.suffix.lower()) or mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        if mime.startswith('text/'):
            mime += '; charset=utf-8'
        self.respond(200, target.read_bytes(), mime, 'no-cache, must-revalidate' if target.suffix in ('.html', '.js', '.css', '.mjs') else 'public, max-age=86400')

    def api(self, path, query):
        db = data()
        method = self.command
        if path.startswith('/api/matching/'):
            from matching_api import handle
            return handle(self, path, query, check, public_guide, CATALOG)
        if method == 'GET' and path == '/api/health':
            return 200, dict(ok=True, time=now_iso())
        if method == 'GET' and path == '/api/meta':
            keys = dict(cities='CITIES', cityGroups='CITY_GROUPS', popularCities='POPULAR_CITIES', regionCount='REGION_COUNT', serviceTypes='SERVICE_TYPES', languages='LANGUAGES', coverPresets='COVER_PRESETS', avatarTones='AVATAR_TONES', otherTracks='OTHER_TRACKS')
            published = [g for g in db['guides'] if g['status'] == 'published']
            return 200, dict(**{k: CATALOG[v] for k, v in keys.items()}, cityCount=len(CATALOG['CITIES']),
                             demoAccount=dict(email='demo@qinghe.cn', password='qinghe123'),
                             stats=dict(guides=len(published), cities=len({g['city'] for g in published}), bookings=len(db['bookings'])))

        if method == 'POST' and path in ('/api/auth/register', '/api/auth/login'):
            body = self.read_body()
            email, password = text(body.get('email'), 120).lower(), str(body.get('password') or '')
            if path.endswith('/register'):
                name = text(body.get('name'), 20)
                check(2 <= len(name) <= 16, '昵称需要 2–16 个字符', 'name')
                check(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email), '请输入有效的邮箱地址', 'email')
                check(6 <= len(password) <= 72, '密码需要 6–72 位', 'password')
                check(not find(db['users'], email=email), '这个邮箱已经注册过了，直接登录吧', 'email', 409)
                salt, digest = hash_password(password)
                user = dict(id=make_id('u'), name=name, email=email, salt=salt, passwordHash=digest, city='', avatarTone=random.choice(CATALOG['AVATAR_TONES']), avatarUrl='', coverUrl='', bio='', photos=[], joinedAt=now_iso())
                db['users'].append(user)
                return 201, dict(token=create_session(user['id']), user=public_user(user))
            check(email and password, '请输入邮箱和密码')
            user = find(db['users'], email=email)
            check(user and verify_password(password, user['salt'], user['passwordHash']), '邮箱或密码不正确', status=401)
            return 200, dict(token=create_session(user['id']), user=public_user(user))

        if method == 'POST' and path == '/api/auth/logout':
            token = self.headers.get('Authorization', '').removeprefix('Bearer ').strip()
            db['sessions'] = [s for s in db['sessions'] if s['token'] != token]
            save()
            return 200, {'ok': True}
        if method == 'GET' and path == '/api/auth/me':
            return 200, {'user': public_user(self.current_user())}

        if method == 'PATCH' and path == '/api/profile':
            user, body = self.current_user(), self.read_body()
            name, city, bio = text(body.get('name'), 20), text(body.get('city'), 20), text(body.get('bio'), 200)
            check(2 <= len(name) <= 16, '昵称需要 2–16 个字符', 'name')
            check(not city or city in CATALOG['CITIES'], '请选择有效的城市', 'city')
            check(len(bio) <= 160, '个人简介最多 160 个字', 'bio')
            user.update(name=name, city=city, bio=bio)
            save()
            return 200, {'user': public_user(user)}

        if method in ('POST', 'DELETE') and path == '/api/profile/photo':
            user, body = self.current_user(), self.read_body()
            kind = text(body.get('kind'), 20)
            check(kind in ('avatar', 'cover', 'gallery'), '图片用途不正确')
            photos = user.setdefault('photos', [])
            if method == 'POST':
                check(kind != 'gallery' or len(photos) < 6, '最多可以保存 6 张照片', status=409)
                url = upload_image(body.get('dataUrl'))
                if kind == 'gallery':
                    photos.append(url)
                else:
                    remove_image(user.get(kind + 'Url'))
                    user[kind + 'Url'] = url
            else:
                if kind == 'gallery':
                    url = text(body.get('url'), 500)
                    check(url in photos, '没有找到这张照片', status=404)
                    photos.remove(url)
                    remove_image(url)
                else:
                    remove_image(user.get(kind + 'Url'))
                    user[kind + 'Url'] = ''
            if kind == 'avatar':
                sync_avatar(user)
            save()
            return (201, dict(user=public_user(user), url=url)) if method == 'POST' else (200, dict(user=public_user(user)))

        if method == 'POST' and path == '/api/uploads':
            self.current_user()
            body = self.read_body()
            check(body.get('kind') == 'guide-cover', '图片用途不正确')
            return 201, {'url': upload_image(body.get('dataUrl'))}

        if method == 'GET' and path in ('/api/conversations', '/api/messages/unread'):
            user = self.current_user()
            conversations = [c for c in db['conversations'] if role_of(c, user['id'])]
            if path.endswith('/unread'):
                return 200, {'count': sum(c.get('unreadTraveler' if role_of(c, user['id']) == 'traveler' else 'unreadGuide', 0) for c in conversations)}
            return 200, {'conversations': [conversation_view(c, user['id']) for c in sorted(conversations, key=lambda c: c['updatedAt'], reverse=True)]}

        if method == 'POST' and path == '/api/conversations':
            user, body = self.current_user(), self.read_body()
            guide = find(db['guides'], id=text(body.get('guideId'), 80), status='published')
            check(guide, '这位地陪暂时无法私聊', status=404)
            check(guide.get('ownerId') != user['id'], '不能和自己发布的服务私聊')
            existing = find(db['conversations'], guideId=guide['id'], travelerId=user['id'])
            if existing:
                return 200, {'conversation': conversation_view(existing, user['id'])}
            now = now_iso()
            conversation = dict(id=make_id('c'), guideId=guide['id'], guideName=guide['name'], guideCover=guide['cover'], guideCity=guide['city'], guideAvatarTone=guide['avatarTone'], guideAvatarUrl=guide.get('avatarUrl', ''), guideOwnerId=guide.get('ownerId'), travelerId=user['id'], travelerName=user['name'], travelerAvatarTone=user['avatarTone'], travelerAvatarUrl=user.get('avatarUrl', ''), createdAt=now, updatedAt=now, unreadTraveler=0, unreadGuide=0)
            db['conversations'].append(conversation)
            if not guide.get('ownerId'):
                db['messages'].append(dict(id=make_id('m'), conversationId=conversation['id'], senderRole='guide', senderId=None, body=f'你好，我是{guide["name"]}。想先了解一下你的出行日期和喜欢的节奏，我可以帮你把路线排得轻松一点。', createdAt=now))
                conversation['unreadTraveler'] = 1
            save()
            return 201, {'conversation': conversation_view(conversation, user['id'])}

        match = re.fullmatch(r'/api/conversations/([^/]+)/messages', path)
        if match:
            user = self.current_user()
            conversation = find(db['conversations'], id=match[1])
            check(conversation and role_of(conversation, user['id']), '对话不存在', status=404)
            role = role_of(conversation, user['id'])
            if method == 'GET':
                conversation['unreadTraveler' if role == 'traveler' else 'unreadGuide'] = 0
                save()
                return 200, dict(conversation=conversation_view(conversation, user['id']), messages=sorted([m for m in db['messages'] if m['conversationId'] == conversation['id']], key=lambda m: m['createdAt']))
            if method == 'POST':
                body = self.read_body()
                message_text = text(body.get('body'), 1000)
                check(message_text, '消息内容不能为空', 'body')
                message = dict(id=make_id('m'), conversationId=conversation['id'], senderRole=role, senderId=user['id'], body=message_text, createdAt=now_iso())
                db['messages'].append(message)
                conversation['updatedAt'] = message['createdAt']
                if role == 'guide' or conversation.get('guideOwnerId'):
                    key = 'unreadTraveler' if role == 'guide' else 'unreadGuide'
                    conversation[key] = conversation.get(key, 0) + 1
                save()
                return 201, dict(message=message, conversation=conversation_view(conversation, user['id']))
            raise ApiError(405, '请求方式不支持')

        if method == 'POST' and path == '/api/ai/polish':
            self.current_user()
            body = self.read_body()
            scene, value = text(body.get('scene'), 20), str(body.get('text') or '').strip()
            limit = {'guide': 600, 'profile': 160}.get(scene)
            check(limit, '润色场景不正确')
            check(len(value) >= 6, '先写几句完整的话，AI 才有素材可以润色', 'text')
            check(len(value) <= limit, f'这段文字不能超过 {limit} 个字', 'text')
            return 200, dict(text=polish_text(value, scene, text(body.get('city'), 20), number(body.get('variant'))), engine='local')

        if method == 'GET' and path == '/api/guides':
            user = self.current_user(False)
            args = {k: v[0] for k, v in query.items()}
            guides = [g for g in db['guides'] if g['status'] == 'published']
            for key, field, all_label in [('city', 'city', '全部城市'), ('service', 'services', '全部服务'), ('language', 'languages', '全部语言')]:
                value = text(args.get(key), 20)
                if value and value != all_label:
                    guides = [g for g in guides if (g[field] == value if key == 'city' else value in g[field])]
            low, high = number(args.get('minPrice')), number(args.get('maxPrice'))
            if low:
                guides = [g for g in guides if g['price'] >= low]
            if high:
                guides = [g for g in guides if g['price'] <= high]
            keyword = text(args.get('q'), 60).lower()
            if keyword:
                guides = [g for g in guides if keyword in ' '.join([g['name'], g['city'], g['headline']] + g.get('tags', []) + g.get('services', [])).lower()]
            sorters = {'recommended': lambda g: (-int(g.get('featured', False)), -g['rating'], -g['orders']), 'price-asc': lambda g: g['price'], 'price-desc': lambda g: -g['price'], 'rating': lambda g: (-g['rating'], -g['reviewCount']), 'popular': lambda g: -g['orders'], 'newest': lambda g: g['createdAt']}
            sort = args.get('sort', 'recommended')
            guides.sort(key=sorters.get(sort, sorters['recommended']), reverse=sort == 'newest')
            return 200, dict(guides=[public_guide(g, user) for g in guides], total=len(guides))

        if method == 'GET' and path == '/api/guides/mine':
            user = self.current_user()
            return 200, {'guides': [public_guide(g, user) for g in sorted(db['guides'], key=lambda g: g['createdAt'], reverse=True) if g.get('ownerId') == user['id']]}

        if method == 'POST' and path == '/api/guides':
            user, body = self.current_user(), self.read_body()
            name, city, headline, bio = (text(body.get(k), limit) for k, limit in [('name', 12), ('city', 20), ('headline', 40), ('bio', 600)])
            price, cover = number(body.get('price')), text(body.get('cover'), 200)
            tone = text(body.get('avatarTone'), 20) or user['avatarTone']
            def choices(key, catalog_key):
                values = body.get(key)
                return list(dict.fromkeys(v for v in values if isinstance(v, str) and v in CATALOG[catalog_key])) if isinstance(values, list) else []
            services, languages = choices('services', 'SERVICE_TYPES'), choices('languages', 'LANGUAGES')
            check(2 <= len(name) <= 12, '接单昵称需要 2–12 个字符', 'name')
            check(city in CATALOG['CITIES'], '请选择服务城市', 'city')
            check(6 <= len(headline) <= 40, '一句话介绍需要 6–40 个字符', 'headline')
            check(len(bio) >= 20, '个人介绍至少写 20 个字，让旅人更了解你', 'bio')
            check(50 <= price <= 3000, '半日价格需要在 ¥50–¥3000 之间', 'price')
            check(services, '请至少选择一种服务类型', 'services')
            check(languages, '请至少选择一种沟通语言', 'languages')
            check(usable_cover(cover), '请选择或导入一张有效的封面图', 'cover')
            check(tone in CATALOG['AVATAR_TONES'], '头像样式不正确', 'avatarTone')
            price = math.floor(price + .5)
            guide = dict(id=make_id('g'), ownerId=user['id'], name=name, city=city, headline=headline, bio=bio, cover=cover, gallery=[cover, '/assets/images/gallery-cafe.jpg', '/assets/images/gallery-tea.jpg'], avatarTone=tone, avatarUrl=user.get('avatarUrl', ''), verified=False, featured=False, rating=5, reviewCount=0, orders=0, responseTime='新入驻 · 24 小时内回复', responseRate='新入驻', languages=languages, services=services, tags=[city + '本地人'] + services[:2], highlights=[city + '本地人私藏路线', '不赶路的轻松节奏', '出发前一对一沟通'], idealFor=['第一次来' + city, '朋友 / 情侣出行', '想轻松玩的人'], price=price, packages=make_packages(city, price), reviews=[], createdAt=now_iso(), status='published')
            db['guides'].insert(0, guide)
            save()
            return 201, {'guide': public_guide(guide, user)}

        match = re.fullmatch(r'/api/guides/([^/]+)', path)
        if match:
            user = self.current_user(False)
            guide = find(db['guides'], id=match[1])
            check(guide, '没有找到这位地陪', status=404)
            owner = user and guide.get('ownerId') == user['id']
            if method == 'GET' and (guide['status'] == 'published' or owner):
                return 200, {'guide': public_guide(guide, user)}
            if method == 'PATCH' and owner:
                body = self.read_body()
                if 'status' in body:
                    check(body['status'] in ('published', 'paused'), '状态不正确')
                    guide['status'] = body['status']
                save()
                return 200, {'guide': public_guide(guide, user)}
            raise ApiError(404 if guide['status'] != 'published' else 405, '该服务已暂停接单' if guide['status'] != 'published' else '请求方式不支持')

        if method == 'POST' and path == '/api/bookings':
            user, body = self.current_user(), self.read_body()
            guide = find(db['guides'], id=text(body.get('guideId'), 60), status='published')
            check(guide, '该服务暂时无法预约', status=404)
            package = find(guide.get('packages', []), id=text(body.get('packageId'), 60))
            check(package, '请选择有效的服务套餐', 'packageId')
            day, time = text(body.get('date'), 10), text(body.get('time'), 5)
            people = number(body.get('people'))
            try:
                check(re.fullmatch(r'\d{4}-\d{2}-\d{2}', day), '请选择有效的出行日期', 'date')
                parsed = date.fromisoformat(day)
            except ValueError:
                raise ApiError(400, '请选择有效的出行日期', 'date')
            check(parsed >= date.today(), '出行日期不能早于今天', 'date')
            check(parsed <= date.today() + timedelta(days=180), '暂只支持预约 180 天内的日期', 'date')
            check(time in CATALOG['TIME_SLOTS'], '请选择开始时间', 'time')
            check(people == int(people) and 1 <= people <= 8, '同行人数需要在 1–8 人之间', 'people')
            check(not any(b['userId'] == user['id'] and b['guideId'] == guide['id'] and b['date'] == day and b['time'] == time and b['status'] in ACTIVE for b in db['bookings']), '这个时间段你已经预约过啦', 'date', 409)
            people = int(people)
            from matching_service import availability_reason, package_hours
            reason = availability_reason(dict(date=day, time=time, hours=package_hours(package), people=people), guide, db)
            check(not reason, reason or '当前档期无法预约', status=409)
            total = quote(package['price'], people)
            extra = total - package['price']
            booking = dict(id=make_id('b'), userId=user['id'], guideId=guide['id'], guideName=guide['name'], guideCity=guide['city'], guideCover=guide['cover'], packageId=package['id'], packageName=package['name'], packageDuration=package['duration'], date=day, time=time, people=people, extraPeopleFee=extra, note=text(body.get('note'), 240), total=total, status='pending', createdAt=now_iso())
            db['bookings'].append(booking)
            save()
            return 201, {'booking': booking}

        if method == 'GET' and path == '/api/bookings/mine':
            user = self.current_user()
            return 200, {'bookings': sorted([b for b in db['bookings'] if b['userId'] == user['id']], key=lambda b: b['createdAt'], reverse=True)}
        match = re.fullmatch(r'/api/bookings/([^/]+)/cancel', path)
        if method == 'PATCH' and match:
            user = self.current_user()
            booking = find(db['bookings'], id=match[1], userId=user['id'])
            check(booking, '没有找到这笔预约', status=404)
            check(booking['status'] in ACTIVE, '这笔预约当前无法取消', status=409)
            booking.update(status='cancelled', cancelledAt=now_iso())
            save()
            return 200, {'booking': booking}
        raise ApiError(404, '接口不存在')


def main():
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '4173'))
    data()  # Validate existing data before accepting any requests.
    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError as error:
        raise SystemExit(f'无法启动 {host}:{port}，请检查端口是否被占用：{error}')
    PID_FILE.write_text(str(os.getpid()), encoding='utf-8')
    server.daemon_threads = False
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    print(f'青禾 · Python 版\nhttp://{host}:{port}\n演示账号：demo@qinghe.cn / qinghe123\n按 Ctrl+C 关闭', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if PID_FILE.exists() and PID_FILE.read_text().strip() == str(os.getpid()):
            PID_FILE.unlink()


if __name__ == '__main__':
    main()
