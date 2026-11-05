"""Candidate constraints, local model loading and reciprocal ranking."""
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import re

from pricing import quote

MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'matching.pt'
_engine = None


def package_hours(package):
    return int(re.search(r'\d+', package['duration'])[0])


def time_window(day, time, hours):
    start = datetime.fromisoformat(day + 'T' + time)
    return start, start + timedelta(hours=hours)


def availability_reason(trip, guide, db):
    preferences = guide.get('matchPreferences')
    if preferences:
        if trip['people'] > preferences['maxPeople']:
            return '超出地陪接待人数'
        if datetime.fromisoformat(trip['date']).weekday() not in preferences['weekdays']:
            return '不在地陪接单星期内'
        if trip['date'] in preferences['blockedDates']:
            return '地陪当天休息'
    start, end = time_window(trip['date'], trip['time'], trip['hours'])
    related = {g['id'] for g in db['guides'] if g['id'] == guide['id'] or
               (guide.get('ownerId') and g.get('ownerId') == guide['ownerId'])}
    for booking in db['bookings']:
        if booking['guideId'] in related and booking['status'] in ('pending', 'confirmed'):
            booked_start, booked_end = time_window(booking['date'], booking['time'], package_hours({'duration': booking['packageDuration']}))
            if start < booked_end and booked_start < end:
                return '行程与已有预约重叠'
    return None


def candidate(trip, guide, db):
    if guide['status'] != 'published':
        return None, '服务已暂停'
    if guide.get('ownerId') == trip['userId']:
        return None, '本人发布的服务'
    if guide['city'] != trip['city']:
        return None, '城市不同'
    if not set(trip['languages']) & set(guide['languages']):
        return None, '没有共同沟通语言'
    if not set(trip['services']).issubset(guide['services']):
        return None, '不提供所需服务'
    packages = [p for p in guide['packages'] if package_hours(p) == trip['hours']]
    if not packages:
        return None, '没有对应时长的套餐'
    package = min(packages, key=lambda p: p['price'])
    total = quote(package['price'], trip['people'])
    if total > trip['budget']:
        return None, '超出整团总预算'
    reason = availability_reason(trip, guide, db)
    if reason:
        return None, reason
    if not guide.get('matchPreferences'):
        return None, '地陪尚未填写双边偏好'
    return dict(packageId=package['id'], packageName=package['name'], total=total), None


def load_engine():
    global _engine
    import torch
    from matching_model import TinyBilateralMatcher, MatcherEnsemble
    timestamp = MODEL_PATH.stat().st_mtime_ns
    if _engine is None or _engine[0] != timestamp:
        torch.set_num_threads(2)
        checkpoint = torch.load(MODEL_PATH, map_location='cpu', weights_only=True)
        if checkpoint.get('kind') == 'ensemble':
            members = []
            for state in checkpoint['members']:
                member = TinyBilateralMatcher(len(checkpoint['vocab']) + 2, **state['config'])
                member.load_state_dict(state['weights'])
                members.append(member)
            model = MatcherEnsemble(members)
        else:
            model = TinyBilateralMatcher(len(checkpoint['vocab']) + 2, **checkpoint.get('config', {}))
            model.load_state_dict(checkpoint['weights'])
        model.eval()
        _engine = timestamp, model, checkpoint['vocab'], checkpoint['metadata']
    return _engine[1:]


def rank_pairs(trips, guides, db):
    import torch
    from matching_model import make_graph, tensor_graph, reciprocal_score
    model, vocab, metadata = load_engine()
    # Both views use the same graph context so a pair receives identical scores.
    context_trips = {t['id']: t for t in db.get('matchTrips', []) if t['status'] == 'open'}
    context_trips.update({t['id']: t for t in trips})
    context_guides = {g['id']: g for g in db['guides']}
    context_guides.update({g['id']: g for g in guides})
    graph = make_graph(sorted(context_trips.values(), key=lambda t: t['id']),
                       sorted(context_guides.values(), key=lambda g: g['id']))
    eligible, excluded = [], Counter()
    for trip in trips:
        for guide in guides:
            offer, reason = candidate(trip, guide, db)
            if reason:
                excluded[reason] += 1
            else:
                eligible.append((trip, guide, offer))
    results = []
    if eligible:
        pairs = torch.tensor([[graph['indices'][('traveler', t['id'])], graph['indices'][('guide', g['id'])]] for t, g, _ in eligible])
        with torch.inference_mode():
            scores = model(tensor_graph(graph, vocab), pairs).tolist()
        for (trip, guide, offer), (traveler_score, guide_score) in zip(eligible, scores):
            shared = sorted(set(trip['interests']) & set(guide['matchPreferences']['interests']))
            results.append(dict(tripId=trip['id'], guideId=guide['id'], offer=offer,
                                travelerScore=round(traveler_score * 100, 1), guideScore=round(guide_score * 100, 1),
                                score=round(reciprocal_score(traveler_score, guide_score) * 100, 1),
                                reasons=['城市、服务、语言、人数、预算与档期满足当前条件'] +
                                (['双方填写的共同兴趣：' + '、'.join(shared)] if shared else [])))
    results.sort(key=lambda r: (-r['score'], r['offer']['total'], r['guideId'], r['tripId']))
    return dict(matches=results, excluded=dict(excluded), modelInfo=metadata,
                graph=dict(nodes=len(graph['nodes']), nodeTypes=dict(Counter(n['kind'] for n in graph['nodes'])),
                           edgeTypes={r: len(e) for r, e in graph['edges'].items()}))
