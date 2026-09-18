from __future__ import annotations
from .models import Candidate, SceneProfile

RISK_LABELS={'fear_or_horror':'恐怖/惊吓元素','violence_possible':'可能有暴力内容','mature_rating':'可能有成人尺度内容','social_embarrassment':'可能有尴尬/社死情节','emotionally_heavy':'情绪可能偏沉重','childish':'可能偏低幼','death_or_grief':'死亡/哀伤主题','infidelity':'不忠/出轨主题','abusive_relationship':'不健康关系','animal_harm':'动物伤害'}
SURPRISE_LABELS={'plot_reveal':'有剧情揭示/反转空间','worldbuilding':'设定或世界观有新鲜感','relationship_turns':'关系发展有变化','comic_payoff':'喜剧包袱/反差感','visual_set_piece':'动作或视觉场面有看点','insight':'信息或观点层面可能有新发现'}
TONE_LABELS={'romantic':'恋爱感明确','sweet':'偏甜','gentle':'温柔舒缓','playful':'轻快活泼','warm':'温暖','realistic':'偏现实','bittersweet':'苦甜交织','dark':'偏暗黑','quirky':'有点怪趣','stylized':'风格化'}

def reason(c:Candidate,p:SceneProfile,evidence:dict|None=None)->dict:
    facts=[]
    if p.source_reference: facts.append(f'参考《{p.source_reference}》的类型/氛围相似性')
    if p.required_signals:
        labels=[]
        if 'funny' in p.required_signals and ('funny' in c.emotion_tags or any('comedy' in g.casefold() for g in c.genres)): labels.append('轻松好笑')
        if 'fast' in p.required_signals and ('fast' in c.pace_tags or 'exciting' in c.emotion_tags): labels.append('节奏偏快')
        if labels: facts.append('核心信号：'+' / '.join(labels))
    if p.required_genres:
        if 'Romance' in p.required_genres and ('romantic' in c.relationship_tags or any('romance' in g.casefold() for g in c.genres)): facts.append('核心条件：恋爱/爱情主线匹配')
        else: facts.append('核心类型匹配：'+' / '.join(p.required_genres[:2]))
    if p.popularity_preference=='niche':
        facts.append('热度倾向：'+{'low':'偏冷门','medium':'非头部热门','unknown':'热度信息不足','high':'相对热门'}.get(c.popularity_bucket or 'unknown','热度未知'))
    if p.relationship_focus and set(p.relationship_focus)&set(c.relationship_tags): facts.append('关系线匹配：'+ ' / '.join(set(p.relationship_focus)&set(c.relationship_tags)))
    shared_mood=[x for x in p.moods if x in c.emotion_tags]
    if shared_mood: facts.append('情绪匹配：'+ ' / '.join(shared_mood))
    shared_tone=[x for x in p.tone_preferences if x in c.tone_tags]
    if shared_tone: facts.append('氛围匹配：'+ ' / '.join(TONE_LABELS.get(x,x) for x in shared_tone))
    if p.runtime_max and c.runtime_minutes: facts.append(f'{c.runtime_minutes} 分钟，满足 ≤{p.runtime_max} 分钟')
    if p.year_min and c.release_year: facts.append(f'{c.release_year} 年，满足年份条件')
    if p.cognitive_load and c.cognitive_load==p.cognitive_load: facts.append('观看负担匹配：'+p.cognitive_load)
    if p.companions and p.companions in c.scene_tags: facts.append('观看场景匹配：'+p.companions)
    watchouts=[RISK_LABELS[tag] for tag in c.risk_tags[:4] if tag in RISK_LABELS]
    surprises=[SURPRISE_LABELS[x] for x in c.surprise_tags[:3] if x in SURPRISE_LABELS]
    evidence=evidence or {}
    caution=None
    if c.understanding_confidence < .58: caution='当前只有简介/类型级证据，具体场景级雷点不能做绝对保证。'
    elif 'risk_detail_unverified' in c.risk_tags: caution='当前数据没有足够细的尺度/家长指南信息，不能保证不存在所有敏感情节。'
    return {'why':'；'.join(facts[:4]) or '在当前候选中综合匹配度较高。','watchouts':watchouts,'surprises':surprises,'caution':caution,'evidence_level':round(c.understanding_confidence,3),'grounded_evidence_types':sorted(evidence.keys())}
