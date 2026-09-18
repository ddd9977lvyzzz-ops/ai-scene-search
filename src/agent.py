from __future__ import annotations
from .intent_parser import parse_intent, clarification_question
from .filtering import hard_filter
from .reranker import rerank
from .reasoner import reason
from .evidence_store import EvidenceStore
from .llm_agent import LLMAgentBrain

RELAXING = {'light', 'relaxing', 'healing'}
HIGH_AROUSAL = {'exciting', 'tense', 'scary', 'thought_provoking'}

def _remove(items: list[str], values: set[str]) -> list[str]:
    return [x for x in items if x not in values]

def apply_relative_commands(profile, text: str) -> None:
    t = text.strip()
    if any(x in t for x in ['更轻松', '轻松一点', '放松一点']):
        profile.moods = _remove(profile.moods, HIGH_AROUSAL)
        for mood in ['light', 'relaxing']:
            if mood not in profile.moods: profile.moods.append(mood)
        profile.cognitive_load = 'low'
    if any(x in t for x in ['刺激一点', '更刺激']):
        profile.moods = _remove(profile.moods, RELAXING)
        if 'exciting' not in profile.moods: profile.moods.append('exciting')
    only_types = {
        '只看电影': 'movie', '只要电影': 'movie',
        '只看电视剧': 'series', '只看剧': 'series',
        '只看综艺': 'variety', '只看纪录片': 'documentary',
        '只看动漫': 'animation', '只看动画': 'animation',
    }
    for key, value in only_types.items():
        if key in t:
            profile.content_types = [value]
            break
    if any(x in t for x in ['不限时长', '时长不限']): profile.runtime_max = None
    if any(x in t for x in ['可以恐怖', '恐怖也可以', '不排斥恐怖']):
        profile.avoid_genres = [x for x in profile.avoid_genres if x != 'Horror']
        profile.avoid_risks = [x for x in profile.avoid_risks if x != 'fear_or_horror']
    if any(x in t for x in ['可以爱情', '爱情也可以']):
        profile.avoid_genres = [x for x in profile.avoid_genres if x != 'Romance']
    if any(x in t for x in ['更冷门', '再小众一点', '小众一点']):
        profile.popularity_preference='niche'
    if any(x in t for x in ['热门一点', '主流一点']):
        profile.popularity_preference='mainstream'
    if any(x in t for x in ['给我点惊喜','大胆一点','更发散','探索一点']):
        profile.exploration_mode='explore'; profile.exploration_strength=max(profile.exploration_strength,.65)
    if any(x in t for x in ['精准一点','别发散','严格匹配','只按条件']):
        profile.exploration_mode='precise'; profile.exploration_strength=0.0

def clarification_options(question: str) -> list[str]:
    if '自己看' in question: return ['一个人看', '和朋友看', '跟家人看', '和对象看']
    if '哪种感觉' in question: return ['轻松一点', '刺激一点', '治愈一点', '想烧脑']
    if '刺激' in question and '动作或悬疑' in question: return ['对，动作/悬疑即可', '我其实可以看恐怖']
    if '想看和排除同一种类型' in question: return ['以想看为准','以排除为准']
    return []

def _quick_actions(profile) -> list[str]:
    actions=['换一批']
    if profile.popularity_preference!='niche': actions.append('再小众一点')
    if profile.exploration_mode=='precise': actions.append('给我点惊喜')
    else: actions.append('精准一点')
    if profile.cognitive_load!='low': actions.append('更轻松一点')
    if not profile.year_min: actions.append('更新一点')
    return actions[:5]

class SceneSearchAgent:
    def __init__(self, retriever, store, event_store=None):
        self.retriever = retriever
        self.store = store
        self.event_store = event_store
        self.evidence_store = EvidenceStore(retriever.con)
        self.brain = LLMAgentBrain()

    def chat(self, session_id: str, text: str):
        state = self.store.get(session_id)
        if state is None: raise KeyError('session_not_found')
        profile, exposed, turn = state
        patch = parse_intent(text)
        profile.merge(patch)
        plan=self.brain.plan(text, profile)
        llm_patch=self.brain.soft_patch(plan)
        if llm_patch is not None:
            profile.merge(llm_patch)
        apply_relative_commands(profile, text)
        turn += 1
        q = clarification_question(profile)
        if not q and plan and plan.get('needs_clarification'):
            q = plan.get('clarification_question')
        if q:
            self.store.save(session_id, profile, exposed, turn)
            if self.event_store: self.event_store.log('clarify_shown', session_id, payload={'turn': turn, 'question': q})
            return {'type':'clarify','session_id':session_id,'turn':turn,'profile':profile.to_dict(),'question':q,'options':clarification_options(q),'agent_mode':self.brain.mode,'llm_plan':plan}

        retrieval_text=(plan or {}).get('query_rewrite') or text
        retrieved = self.retriever.retrieve(retrieval_text, profile, limit=140, exclude_ids=exposed)
        kept, dropped = hard_filter(retrieved, profile)
        top_k=1 if ((plan or {}).get('decision_style')=='pick_one' or any(x in text for x in ['只给我一个','直接选一个','替我选一个','帮我拍板','别给列表'])) else 5
        ranked = rerank(kept, profile, top_k=top_k)
        if not ranked:
            self.store.save(session_id, profile, exposed, turn)
            counter={}
            for _,rs in dropped:
                for rr in rs: counter[rr]=counter.get(rr,0)+1
            blocker=max(counter,key=counter.get) if counter else 'catalog_no_match'
            if self.event_store: self.event_store.log('no_match',session_id,payload={'turn':turn,'blocker':blocker})
            return {'type':'no_match','session_id':session_id,'turn':turn,'profile':profile.to_dict(),'blocker':blocker,
                    'suggestion':'我不会偷偷放宽硬条件。可以只放宽一个条件后重试，例如时长、年份、平台或明确类型。',
                    'debug':{'retrieved':len(retrieved),'after_hard_filter':len(kept),'dropped':len(dropped)}}

        result=[]
        for c in ranked:
            chunks=self.evidence_store.get(c.content_id,spoiler_tolerance=profile.spoiler_tolerance,limit=8)
            evidence=self.evidence_store.summarize(chunks)
            result.append({
                'content_id':c.content_id,'title':c.title,'content_type':c.content_type,'release_year':c.release_year,
                'runtime_minutes':c.runtime_minutes,'genres':c.genres,'poster_url':c.poster_url,'platforms':c.platforms,
                'tone_tags':c.tone_tags,'surprise_tags':c.surprise_tags,'popularity_bucket':c.popularity_bucket,
                'score':c.score,'score_breakdown':c.score_breakdown,'evidence':evidence,**reason(c,profile,evidence=evidence)
            })
        exposed.extend([x['content_id'] for x in result])
        self.store.save(session_id, profile, exposed, turn)
        if self.event_store:
            self.event_store.log('recommendation_shown',session_id,payload={
                'turn':turn,'result_ids':[x['content_id'] for x in result],'retrieved':len(retrieved),
                'after_hard_filter':len(kept),'dropped':len(dropped),'exploration_mode':profile.exploration_mode,
            })
        return {'type':'recommend','session_id':session_id,'turn':turn,'profile':profile.to_dict(),'results':result,
                'intent_engine':'rules+llm_soft' if llm_intent_enabled() else 'rules+semantic_retrieval',
                'quick_actions':_quick_actions(profile),
                'debug':{'retrieved':len(retrieved),'after_hard_filter':len(kept),'dropped':len(dropped)}}
