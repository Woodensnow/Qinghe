"""Explicitly synthetic teaching data, never fabricated real user feedback."""
import random

INTERESTS = ['咖啡', '美食', '历史', '摄影', '自然', '亲子']
PACES = ['慢慢逛', '适中', '紧凑']
SERVICE_FOR = dict(zip(INTERESTS, ['城市漫步', '美食探店', '城市漫步', '拍照陪游', '周边包车', '亲子出行']))
PHRASES = {'咖啡': ['喝咖啡逛小店', '寻找咖啡馆和拿铁'], '美食': ['吃本地小吃逛菜市场', '寻找老字号美食'],
           '历史': ['听古建筑背后的历史故事', '探访老街和历史遗迹'], '摄影': ['带相机去河边拍照', '拍自然的旅行照片'],
           '自然': ['去山野和湖边看风景', '喜欢自然和户外路线'], '亲子': ['带孩子轻松出游', '适合亲子家庭一起玩']}

# Topic sentence templates are disjoint across partitions. Labels come from
# latent generated preferences, never reverse-parsing the evaluation text.
PHRASE_BANKS = {
    'train': PHRASES,
    'validation': {'咖啡': ['想去喝手冲咖啡', '沿街找一家咖啡店坐坐'],
                   '美食': ['边走边品尝本地美食', '美食路线最好有小馆子'],
                   '历史': ['想了解这里的历史文化', '欣赏历史建筑与街区'],
                   '摄影': ['希望安排摄影取景点', '摄影时想留足等待光线的时间'],
                   '自然': ['想亲近自然换换空气', '自然风光比热闹商圈更吸引我'],
                   '亲子': ['亲子行程想留出休息时间', '安排一家人喜欢的亲子活动']},
    'test': {'咖啡': ['在咖啡香里认识城市', '咖啡是这次慢游的主题'],
             '美食': ['美食清单上都是街坊爱吃的店', '用地道美食记录旅程'],
             '历史': ['从历史遗存里读懂一座城', '聊聊城市历史的来龙去脉'],
             '摄影': ['用摄影记录沿途的日常', '摄影爱好者想寻找特别的视角'],
             '自然': ['自然里的安静让我放松', '把时间留给自然与风景'],
             '亲子': ['亲子旅行希望孩子也参与', '把亲子体验变成全家的回忆']}
}

# A prospective confirmation set reserved after the first experiment. The
# exploratory test in report.json is never relabelled as untouched evidence.
PHRASE_BANKS['confirmation'] = {
    '咖啡': ['咖啡馆之间的漫步很适合我', '想把咖啡时间排进行程'],
    '美食': ['美食之旅想尝尝居民熟悉的味道', '美食和市井生活是旅行的重点'],
    '历史': ['沿着历史线索走访城市', '历史文化是我最关心的话题'],
    '摄影': ['这趟出行为了摄影与记录', '计划留一段摄影创作时间'],
    '自然': ['自然景色会让我多停留一会儿', '希望体验自然里的慢节奏'],
    '亲子': ['亲子活动要让大人孩子都开心', '想找适合亲子相处的路线']}


# Label-neutral free text (logistics, personality, communication). No interest,
# pace, service or city words, so it never changes a label. Banks are disjoint
# across partitions; train is the richest because only train text builds the
# vocabulary, which leaves later splits with unseen characters like real users.
GUIDE_NOTES = {
    'train': ['我是土生土长的本地人，在这里住了十几年。', '做过五年的活动策划，很会安排时间和路线。',
              '你只要告诉我想去哪里，剩下的交给我来准备。', '不进购物店，也不赶场，一切按你的想法来。',
              '平时喜欢和朋友聊天，见面就像老朋友一样。', '出发前会和你确认集合地点，下雨也有备用方案。',
              '可以讲普通话和英语，外地朋友不用担心沟通。', '我知道哪些地方人少，可以帮你避开排队。',
              '接待过很多一个人出来走走的旅客，也接待过大家庭。', '性格开朗，有耐心，路上会照顾好每一位同行的人。',
              '我会提前查好天气和交通，晚上也能送你回酒店。', '如果你是第一次来，我会把要点讲清楚，让你玩得放心。',
              '周末和节假日也可以约，最好提前两三天联系我。', '我们可以边走边聊，听听这座城市里普通人的生活。',
              '有问题随时发消息给我，一般半小时内回复。'],
    'validation': ['在本地生活多年，对大街小巷都很熟悉。', '以前做过酒店前台，接待外地客人很有经验。',
                   '行程可以随时调整，你累了我们就停下来歇歇。', '喜欢交朋友，很多客人后来都成了朋友。',
                   '集合时间和地点会提前一天发给你。'],
    'test': ['从小在这里长大，熟悉每条街的变化。', '当过几年导游，讲解清楚，也很守时。',
             '带过不少外地和外国的客人，沟通没问题。', '会根据你的体力调整步行距离。',
             '约好之后我会建一个群，方便随时联系。'],
    'confirmation': ['在这座城里工作生活快十年了。', '做事细心，会把每个环节都提前安排好。',
                     '脾气好，很少让客人等待。', '也欢迎第一次见面的朋友提前语音聊聊。',
                     '遇到临时变化，我会第一时间告诉你。']}
TRAVELER_NOTES = {
    'train': ['这是我第一次来，希望行程轻松一点。', '我们一共两个人，不想太早出门。', '想找一位靠谱的本地朋友带路。',
              '预算有限，希望路线安排得合理。', '晚上想早点回酒店休息。', '不太会做攻略，希望有人帮忙规划。',
              '朋友第一次出远门，路上需要多照顾。', '希望向导性格好、好沟通。', '下午有空，可以多走几个地方。',
              '我说话比较直接，有想法会提前讲。', '这次是出差顺便玩一下，时间不多。', '不喜欢人太多的景点，安静一些更好。'],
    'validation': ['第一次一个人旅行，有点紧张。', '想请当地人带我们走走。', '行程不要太满，中午想休息一下。',
                   '同行的长辈腿脚不太方便。', '希望能提前沟通好集合时间。'],
    'test': ['这趟旅行想放松心情。', '我们是三个大学同学一起出来玩。', '希望路线顺一点，少走回头路。',
             '对当地不熟，需要有人带着。', '行程时间可以灵活一些。'],
    'confirmation': ['这次出来就是想换个环境。', '希望向导守时，回复消息快。', '一家人难得出门，想玩得轻松。',
                     '不想在路上花太多时间。', '有什么注意事项希望提前告诉我。']}


def synthetic_profiles(seed=42, travelers=36, guides=24, split='train'):
    rng = random.Random(seed)
    trips, providers = [], []
    cities = ['苏州', '上海', '杭州']
    phrases = PHRASE_BANKS[split]
    for i in range(travelers):
        interests = rng.sample(INTERESTS, rng.choice([1, 2]))
        trips.append(dict(id=f'synthetic_t_{split}_{seed}_{i}', city=rng.choice(cities),
                          services=list(dict.fromkeys(SERVICE_FOR[k] for k in interests)), languages=['中文'],
                          interests=interests, paces=[rng.choice(PACES)],
                          description='，'.join(rng.choice(phrases[k]) for k in interests)))
    for i in range(guides):
        interests = rng.sample(INTERESTS, rng.choice([1, 2, 3]))
        preferred = rng.sample(INTERESTS, rng.choice([1, 2]))
        providers.append(dict(id=f'synthetic_g_{split}_{seed}_{i}', city=rng.choice(cities),
                              services=list(dict.fromkeys(SERVICE_FOR[k] for k in interests)), languages=['中文'],
                              expertiseInterests=interests,
                              headline='，'.join(rng.choice(phrases[k]) for k in interests),
                              bio='愿意认真规划路线，并在出发前沟通。',
                              matchPreferences=dict(interests=preferred, paces=[rng.choice(PACES)],
                                                    text='期待喜欢' + '、'.join(preferred) + '的旅人')))
    # Separate generator: profiles and labels stay identical to the text-only version.
    filler = random.Random(f'notes-{split}-{seed}')
    for trip in trips:
        notes = filler.sample(TRAVELER_NOTES[split], filler.randint(0, min(4, len(TRAVELER_NOTES[split]))))
        trip['description'] = '。'.join([trip['description']] + [n.rstrip('。') for n in notes])
    for guide in providers:
        guide['bio'] += ''.join(filler.sample(GUIDE_NOTES[split], filler.randint(1, min(6, len(GUIDE_NOTES[split])))))
    return trips, providers


def teaching_targets(trip, guide):
    """Asymmetric weak labels from generated preferences, not acceptance events."""
    guide_topics = set(guide['expertiseInterests'])
    preference = guide['matchPreferences']
    interest_fit = len(set(trip['interests']) & guide_topics) / len(trip['interests'])
    service_fit = len(set(trip['services']) & set(guide['services'])) / len(trip['services'])
    customer_fit = len(set(trip['interests']) & set(preference['interests'])) / len(preference['interests'])
    pace = float(bool(set(trip['paces']) & set(preference['paces'])))
    return [.65 * interest_fit + .25 * service_fit + .10 * pace, .70 * customer_fit + .30 * pace]
