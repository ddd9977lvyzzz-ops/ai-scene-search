from __future__ import annotations
import math, re
from datetime import datetime, timezone
from .models import MemoryItem

STOP={'你','我','的','了','吗','呢','是','什么','记得','自己','用户','最近','一下','想','喜欢'}

def tokens(text:str)->set[str]:
    latin=re.findall(r'[A-Za-z0-9_]+',text.lower())
    zh=[c for c in re.findall(r'[\u4e00-\u9fff]',text) if c not in STOP]
    bigrams=[text[i:i+2] for i in range(len(text)-1) if all('\u4e00'<=c<='\u9fff' for c in text[i:i+2])]
    return set(latin+zh+bigrams)

def jaccard(a:str,b:str)->float:
    x,y=tokens(a),tokens(b); return len(x&y)/max(1,len(x|y))

def answer_support(query:str, mem:MemoryItem)->float:
    q=query; t=mem.text; score=0.0
    if any(k in q for k in ['喜欢什么','喜欢吃什么','偏好','爱看什么','喜欢看什么']):
        if mem.memory_type in {'preference','behavior_summary','explicit_feedback'}: score += 0.75
        if any(k in t for k in ['每天','经常','连续','总是','常看','常吃','最喜欢','喜欢']): score += 0.2
        if any(k in t for k in ['问AI','问过','记得自己喜欢','喜欢吃什么吗','喜欢看什么吗']): score -= 0.7
    if any(k in q for k in ['最近','这几天','最近在']):
        if mem.memory_type in {'recent_behavior','behavior_summary'}: score += 0.7
    return max(0.0,min(1.0,score))

def recency(created_at:str)->float:
    try:
        dt=datetime.fromisoformat(created_at.replace('Z','+00:00'))
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        days=max(0,(datetime.now(timezone.utc)-dt).days)
        return math.exp(-days/45)
    except Exception: return 0.5

def score_memory(query:str, mem:MemoryItem)->dict:
    semantic=jaccard(query,mem.text); support=answer_support(query,mem); recent=recency(mem.created_at); evidence=max(0,min(1,mem.evidence_strength))
    total=0.18*semantic + 0.52*support + 0.15*recent + 0.15*evidence
    return {'semantic_similarity':round(semantic,4),'answer_support':round(support,4),'recency':round(recent,4),'evidence_strength':round(evidence,4),'score':round(total,4)}

def retrieve_memories(query:str, memories:list[MemoryItem], k:int=5):
    ranked=[]
    for m in memories:
        s=score_memory(query,m); ranked.append((s['score'],m,s))
    ranked.sort(key=lambda x:x[0],reverse=True)
    return ranked[:k]
