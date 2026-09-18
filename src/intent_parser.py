from __future__ import annotations
import re
from .models import SceneProfile

# The parser is deliberately inspectable. Exact facts become structured constraints; ambiguous
# taste language becomes soft preference. A few phrases (e.g. “好笑”) are strong enough to
# become required_signals so sparse movie metadata cannot surface obviously wrong titles.
MOOD_MAP = {
    '轻松':'light','放松':'relaxing','治愈':'healing','搞笑':'funny','好笑':'funny','逗':'funny','下饭':'light',
    '刺激':'exciting','紧张':'tense','烧脑':'thought_provoking','动脑':'thought_provoking',
    '感动':'emotional','温柔':'healing','吓人':'scary','恐怖':'scary','浪漫':'romantic','甜':'romantic',
}
TYPE_MAP = {
    '电影':'movie','影片':'movie','电视剧':'series','连续剧':'series','剧集':'series','追剧':'series',
    '综艺':'variety','纪录片':'documentary','动漫':'animation','动画':'animation','动画片':'animation',
}
GENRE_MAP = {
    '喜剧':'Comedy','搞笑片':'Comedy','科幻':'Sci-Fi','悬疑':'Thriller','推理':'Mystery','犯罪':'Crime',
    '动作':'Action','爱情':'Romance','恋爱':'Romance','纯爱':'Romance','甜宠':'Romance','恐怖':'Horror',
    '家庭':'Family','奇幻':'Fantasy','冒险':'Adventure','青春':'Coming-of-age','音乐':'Music',
}
PLATFORM_MAP = {
    '腾讯视频':'tencent_video','爱奇艺':'iqiyi','优酷':'youku','芒果':'mango_tv','芒果TV':'mango_tv',
    'Netflix':'netflix','netflix':'netflix','网飞':'netflix',
}
TONE_MAP = {
    '甜宠':'sweet','甜一点':'sweet','很甜':'sweet','小甜':'sweet','温柔':'gentle','克制':'gentle',
    '轻盈':'gentle','现实':'realistic','写实':'realistic','成熟':'realistic','苦涩':'bittersweet','酸涩':'bittersweet',
    '暗黑':'dark','黑暗':'dark','沙雕':'playful','欢乐':'playful','小清新':'warm','暖':'warm',
    '怪诞':'quirky','古怪':'quirky','风格化':'stylized','视觉系':'stylized','不俗套':'quirky',
}
PACE_MAP = {
    '节奏快':'fast','快节奏':'fast','推进快':'fast','不拖沓':'fast',
    '节奏慢':'slow','慢节奏':'slow','慢热':'slow','舒缓':'slow',
}
NEG_PREFIXES = ['不要','不看','别','排除','不想看','避开']


def _negated(t: str, term: str) -> bool:
    return any(prefix + term in t for prefix in NEG_PREFIXES)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def parse_intent(text: str) -> SceneProfile:
    t = text.strip()
    p = SceneProfile()

    # Reference-title exploration: similarity is a soft anchor, never a replacement for explicit constraints.
    ref = re.search(r'(?:类似|像|接近|跟|和)\s*[《「『"]([^》」』"]{1,50})[》」』"](?:一样|类似)?', t)
    if not ref:
        ref = re.search(r'[《「『"]([^》」』"]{1,50})[》」』"]\s*(?:这种|这类|类似)', t)
    if ref:
        p.source_reference = ref.group(1).strip()

    # Region / language. “国产剧” is both language/region and type, not a genre.
    if any(x in t for x in ['国产剧','中国电视剧','大陆剧','国剧','国产电视剧']):
        _add_unique(p.content_types, 'series'); p.language='Chinese'
    elif any(x in t for x in ['国产片','华语片','中国电影']):
        _add_unique(p.content_types, 'movie'); p.language='Chinese'

    if re.search(r'(?:类似|像|这种|这类|这样的).{0,60}?(?:的)?剧(?:[，。！？、]|$|但|不|要)', t):
        _add_unique(p.content_types, 'series')

    # Companions and occasion are scenario features, not mandatory genre filters.
    if any(x in t for x in ['一个人','自己看','自己追','独处']): p.companions='solo'
    elif any(x in t for x in ['爸妈','父母','家人','全家']): p.companions='family'
    elif any(x in t for x in ['朋友','同学','聚会','室友']): p.companions='friends'
    elif any(x in t for x in ['情侣','对象','男朋友','女朋友','约会','两个人看']): p.companions='couple'

    if '聚会' in t: p.scene='party'
    elif any(x in t for x in ['睡前','深夜','晚上躺着','躺床上']): p.scene='late_night'
    elif '通勤' in t: p.scene='commute'
    elif any(x in t for x in ['周末','周六','周日']): p.scene='weekend'
    elif any(x in t for x in ['吃饭','饭后','下饭']): p.scene='meal'

    # Mood / cognitive load.
    for k,v in MOOD_MAP.items():
        if k in t and not _negated(t, k): _add_unique(p.moods, v)
    if any(x in t for x in ['无脑','不用动脑','别太烧脑','不要烧脑','低负担','边吃边看','不费脑','脑子不想转']):
        p.cognitive_load='low'
    elif any(x in t for x in ['烧脑','认真看','高信息量','需要动脑']):
        p.cognitive_load='high'

    # “好笑/搞笑” is not merely a vague mood: without comedy evidence a result is plainly wrong.
    if any(x in t for x in ['好笑','搞笑','能笑','笑点','逗一点','欢乐一点']) and not any(x in t for x in ['有点好笑','带点搞笑']):
        _add_unique(p.required_signals, 'funny')
    if any(x in t for x in ['节奏快','快节奏','推进快','不拖沓']):
        _add_unique(p.required_signals, 'fast')
    if any(x in t for x in ['适合全家','全家都能看','老少皆宜','适合爸妈']):
        _add_unique(p.audience_preferences, 'family')

    # Explicit type and genre.
    for k,v in TYPE_MAP.items():
        if k in t: _add_unique(p.content_types, v)
    for k,v in GENRE_MAP.items():
        if k not in t: continue
        if _negated(t, k):
            _add_unique(p.avoid_genres, v)
        else:
            _add_unique(p.genres, v)
            # Explicit genre words are strict unless phrased as a weak element.
            weak = any(x + k in t for x in ['有点','一点','带点','有一些']) or any(x in t for x in [f'{k}元素', f'{k}线也可以'])
            if not weak: _add_unique(p.required_genres, v)
            # Only an explicit 电影 expression locks the format. In product language, “恋爱片/爱情片”
            # is treated as a broad audiovisual request (movie or series) unless the user explicitly says 电影.
            if re.search(re.escape(k) + r'电影', t): _add_unique(p.content_types, 'movie')

    # Colloquial romance phrases.
    if any(x in t for x in ['恋爱片','爱情片','纯爱片','小甜剧','甜宠剧','恋爱剧','爱情剧']):
        _add_unique(p.genres, 'Romance'); _add_unique(p.required_genres, 'Romance'); _add_unique(p.relationship_focus, 'romantic')
        if any(x in t for x in ['恋爱电影','爱情电影','纯爱电影','恋爱片','爱情片','纯爱片']): _add_unique(p.content_types, 'movie')
        if any(x in t for x in ['恋爱剧','爱情剧','小甜剧','甜宠剧']): _add_unique(p.content_types, 'series')
    if any(x in t for x in ['恋爱','爱情','感情线','情侣关系','CP感','cp感']): _add_unique(p.relationship_focus, 'romantic')
    if any(x in t for x in ['成年人恋爱','成人恋爱','成熟恋爱','成年人的爱情']):
        _add_unique(p.relationship_focus, 'romantic'); _add_unique(p.audience_preferences, 'adult'); _add_unique(p.tone_preferences, 'realistic')

    # Tone / pace.
    for k,v in TONE_MAP.items():
        if k in t and not _negated(t, k): _add_unique(p.tone_preferences, v)
    for k,v in PACE_MAP.items():
        if k in t and not _negated(t, k): _add_unique(p.pace_preferences, v)
    if any(x in t for x in ['节奏快','快节奏']): _add_unique(p.moods, 'exciting')

    # Popularity / quality / discovery.
    if any(x in t for x in ['小众','冷门','不热门','非热门','宝藏片','宝藏剧','少有人看','不想看爆款']):
        p.popularity_preference='niche'
    elif any(x in t for x in ['热门','爆款','大家都在看','大众一点','主流一点']):
        p.popularity_preference='mainstream'
    if any(x in t for x in ['高分','口碑好','评价好','评分高']): p.quality_preference='acclaimed'

    if any(x in t for x in ['给我点惊喜','有点意外','想探索','探索一下','换个口味','打开新世界','大胆一点','不要太保守']):
        p.exploration_mode='explore'; p.exploration_strength=0.65
    elif any(x in t for x in ['可以稍微发散','稍微探索','别太死板']):
        p.exploration_mode='balanced'; p.exploration_strength=0.3
    if any(x in t for x in ['反转','反转多','剧情反转']): _add_unique(p.surprise_preferences, 'plot_reveal')
    if any(x in t for x in ['世界观','设定惊喜','脑洞']): _add_unique(p.surprise_preferences, 'worldbuilding')
    if any(x in t for x in ['视觉惊喜','画面好看','视觉奇观']): _add_unique(p.surprise_preferences, 'visual_set_piece')
    if any(x in t for x in ['不俗套','有新鲜感','有点新东西']): _add_unique(p.surprise_preferences, 'fresh_premise')

    # Negative constraints. Only explicit negatives become hard gates.
    if any(x in t for x in ['不要恐怖','不看恐怖','别吓人','不要吓人','别有鬼']):
        _add_unique(p.avoid_genres, 'Horror'); _add_unique(p.avoid_risks, 'fear_or_horror')
    if any(x in t for x in ['不要尴尬','不要太尴尬','别太尴尬','社死少一点']): _add_unique(p.avoid_risks, 'social_embarrassment')
    if any(x in t for x in ['别有亲密戏','不要亲密戏','适合爸妈','不要大尺度']): _add_unique(p.avoid_risks, 'mature_rating')
    if any(x in t for x in ['不要低幼','不要太低幼','别太低幼','不想太低幼']): _add_unique(p.avoid_risks, 'childish')
    if any(x in t for x in ['不要太虐','不要虐','别太虐','不想看虐的','别太沉重']): _add_unique(p.avoid_risks, 'emotionally_heavy')
    if any(x in t for x in ['不要暴力','别太暴力','不想看打打杀杀']): _add_unique(p.avoid_risks, 'violence_possible')
    if any(x in t for x in ['不要爱情','不看爱情','排除爱情','不要恋爱线']):
        _add_unique(p.avoid_genres, 'Romance'); p.relationship_focus=[x for x in p.relationship_focus if x!='romantic']

    # Runtime.
    runtime_patterns = [
        (r'(\d+)\s*分钟(?:内|以内|以下)', 1),
        (r'(\d+)\s*小时(?:内|以内|以下)', 60),
        (r'两小时(?:内|以内|以下)?', 120),
        (r'一个半小时(?:内|以内|以下)?', 90),
    ]
    for pat,mul in runtime_patterns:
        m=re.search(pat,t)
        if m:
            try: p.runtime_max=int(m.group(1))*mul
            except IndexError: p.runtime_max=mul
            break
    if p.runtime_max is None:
        if '两小时' in t: p.runtime_max=120
        elif '90分钟' in t or '九十分钟' in t: p.runtime_max=90

    # Year.
    ym=re.search(r'(20\d{2})\s*(?:年)?(?:以后|之后|起|以来)',t)
    if ym: p.year_min=int(ym.group(1))
    elif '近五年' in t: p.year_min=2022
    elif any(x in t for x in ['新一点','更新一点','近几年']): p.year_min=2020

    for k,v in PLATFORM_MAP.items():
        if k in t: _add_unique(p.platforms, v)

    # Conflict checks.
    if ('特别吓人' in t or '越吓人越好' in t) and ('不要恐怖' in t or '不看恐怖' in t): p.conflicts.append('want_scary_vs_avoid_horror')
    if set(p.required_genres) & set(p.avoid_genres): p.conflicts.append('required_genre_vs_avoid_genre')

    signals = [
        p.companions,p.scene,p.moods,p.cognitive_load,p.content_types,p.genres,p.required_signals,
        p.relationship_focus,p.audience_preferences,p.tone_preferences,p.pace_preferences,p.runtime_max,p.year_min,
        p.avoid_genres,p.avoid_risks,p.platforms,p.popularity_preference,p.quality_preference,p.surprise_preferences,p.source_reference,
    ]
    filled=sum(bool(x) for x in signals)
    strong_core=bool(p.required_genres or p.required_signals or (p.relationship_focus and p.popularity_preference) or (p.genres and p.tone_preferences))
    p.confidence=min(0.98,0.27+filled*0.07+(0.16 if strong_core else 0))
    return p


def clarification_question(p: SceneProfile) -> str | None:
    if p.conflicts:
        if 'required_genre_vs_avoid_genre' in p.conflicts:
            return '你同时说了想看和排除同一种类型。以“想看”为准，还是以“排除”为准？'
        return '你说的“刺激”可以是动作或悬疑，但不要恐怖元素，对吗？'

    # Strong content or scenario briefs should get a first recommendation instead of a questionnaire.
    content_signal=bool(p.required_genres or p.required_signals or p.genres or p.relationship_focus or p.tone_preferences or p.popularity_preference or p.quality_preference or p.content_types or p.source_reference)
    scene_signal=bool(p.companions or p.scene or p.moods or p.cognitive_load)
    if (content_signal or (scene_signal and p.confidence>=0.48)) and p.confidence>=0.46: return None
    if not content_signal and p.companions is None: return '这次是自己看，还是和别人一起看？'
    if not p.moods and not p.genres and not p.relationship_focus and not p.tone_preferences: return '你更想获得哪种感觉：轻松、刺激、治愈，还是烧脑？'
    if not content_signal and not scene_signal: return '你更想看电影、剧集，还是都可以？'
    return None
