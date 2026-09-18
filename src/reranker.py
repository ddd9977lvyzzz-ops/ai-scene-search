from __future__ import annotations
from .models import Candidate, SceneProfile

def _match_count(wanted:list[str], actual:list[str]) -> float:
    if not wanted: return 0.0
    return len(set(wanted)&set(actual))/max(1,len(wanted))

def _genre_score(c:Candidate,p:SceneProfile)->float:
    if not p.genres: return 0.0
    hits=0
    for g in p.genres:
        if g=='Romance' and 'romantic' in c.relationship_tags: hits+=1; continue
        if any(g.casefold() in x.casefold() or x.casefold() in g.casefold() for x in c.genres): hits+=1
    return hits/max(1,len(p.genres))

def _required_signal_score(c:Candidate,p:SceneProfile)->float:
    if not p.required_signals: return 0.0
    hits=0
    for x in p.required_signals:
        if x=='funny' and ('funny' in c.emotion_tags or 'playful' in c.tone_tags or any('comedy' in g.casefold() for g in c.genres)): hits+=1
        elif x=='fast' and ('fast' in c.pace_tags or 'exciting' in c.emotion_tags or any(g.casefold() in {'action','adventure','thriller'} for g in c.genres)): hits+=1
    return hits/max(1,len(p.required_signals))

def _audience_score(c:Candidate,p:SceneProfile)->float:
    if not p.audience_preferences: return 0.0
    scores=[]
    for a in p.audience_preferences:
        if a=='family':
            safe = not set(c.risk_tags)&{'mature_rating','fear_or_horror','violence_possible','social_embarrassment'}
            scores.append(1.0 if ('family' in c.audience_tags or any('family' in g.casefold() for g in c.genres)) and safe else (0.65 if safe else 0.0))
        elif a=='adult': scores.append(0.15 if 'kids' in c.audience_tags or 'childish' in c.risk_tags else 0.75)
        else: scores.append(1.0 if a in c.audience_tags else 0.0)
    return sum(scores)/len(scores)

def _scene_fit(c:Candidate,p:SceneProfile)->float:
    signals=[]; genres={g.casefold() for g in c.genres}; risks=set(c.risk_tags)
    if p.companions=='family':
        safe=not risks&{'mature_rating','fear_or_horror','violence_possible','social_embarrassment'}
        base=0.85 if safe else 0.18
        if 'family' in c.audience_tags or 'family' in genres: base=min(1.0,base+0.15)
        if 'funny' in c.emotion_tags or 'comedy' in genres: base=min(1.0,base+0.08)
        signals.append(base)
    elif p.companions=='friends':
        base=0.35
        if 'funny' in c.emotion_tags or 'comedy' in genres or 'playful' in c.tone_tags: base+=0.35
        if 'party' in c.scene_tags or 'background_friendly' in c.watching_tags: base+=0.2
        if 'tense' in c.emotion_tags or 'exciting' in c.emotion_tags: base+=0.08
        signals.append(min(1.0,base))
    elif p.companions=='couple':
        base=0.35+(0.45 if 'romantic' in c.relationship_tags or 'romance' in genres else 0)
        if 'social_embarrassment' in risks: base-=0.12
        signals.append(max(0,min(1,base)))
    elif p.companions=='solo':
        base=0.55
        if 'solo' in c.scene_tags or c.content_type in {'series','documentary'}: base+=0.22
        signals.append(min(1.0,base))

    if p.scene=='meal':
        base=0.25
        if c.cognitive_load=='low': base+=0.3
        if set(c.emotion_tags)&{'light','relaxing','funny'}: base+=0.3
        if 'background_friendly' in c.watching_tags: base+=0.15
        if risks&{'mature_rating','fear_or_horror'}: base-=0.2
        signals.append(max(0,min(1,base)))
    elif p.scene=='party':
        base=0.3
        if 'funny' in c.emotion_tags or 'comedy' in genres: base+=0.38
        if 'party' in c.scene_tags or 'friends' in c.scene_tags: base+=0.22
        signals.append(min(1.0,base))
    elif p.scene=='late_night':
        base=0.45
        if set(c.emotion_tags)&{'healing','relaxing','light'} or set(c.tone_tags)&{'gentle','warm'}: base+=0.35
        if 'scary' in c.emotion_tags and 'scary' not in p.moods: base-=0.25
        signals.append(max(0,min(1,base)))
    elif p.scene=='commute':
        signals.append(min(1.0,0.4+(0.45 if 'commute' in c.scene_tags or 'short_session' in c.scene_tags else 0)))
    elif p.scene=='weekend':
        signals.append(0.85 if 'weekend' in c.scene_tags else 0.55)
    return sum(signals)/len(signals) if signals else 0.0

def _pop_score(c:Candidate,p:SceneProfile)->float:
    b=c.popularity_bucket or 'unknown'
    if p.popularity_preference=='niche': return {'low':1.0,'medium':0.70,'unknown':0.42,'high':0.06}.get(b,0.4)
    if p.popularity_preference=='mainstream': return {'high':1.0,'medium':0.74,'unknown':0.4,'low':0.12}.get(b,0.4)
    return 0.5

def _novelty(c:Candidate)->float:
    return {'low':1.0,'medium':0.65,'unknown':0.38,'high':0.12}.get(c.popularity_bucket or 'unknown',0.38)

def _overlap(a:Candidate,b:Candidate)->float:
    sa=set(a.tone_tags+a.theme_tags+a.relationship_tags+a.emotion_tags+a.genres)
    sb=set(b.tone_tags+b.theme_tags+b.relationship_tags+b.emotion_tags+b.genres)
    return len(sa&sb)/len(sa|sb) if sa and sb else 0.0

def _risk_penalty(c:Candidate,p:SceneProfile)->float:
    risks=set(c.risk_tags); penalty=0.0
    if p.companions=='family':
        penalty += 0.24*len(risks&{'mature_rating','fear_or_horror'})
        penalty += 0.12*len(risks&{'violence_possible','social_embarrassment'})
    if p.scene=='meal': penalty += 0.12*len(risks&{'mature_rating','fear_or_horror'})
    if p.moods and set(p.moods)&{'light','relaxing','healing'}: penalty += 0.12*len(risks&{'emotionally_heavy','fear_or_horror'})
    return min(0.42,penalty)

def _metadata_quality(c:Candidate)->float:
    signals=0
    if c.description and len(c.description.strip())>=45: signals+=1
    if [g for g in c.genres if g.casefold() not in {'film','tv'}]: signals+=1
    if c.emotion_tags: signals+=1
    if c.relationship_tags or c.theme_tags or c.tone_tags: signals+=1
    return signals/4

def rerank(cands:list[Candidate], p:SceneProfile, top_k:int=5):
    for c in cands:
        mood=_match_count(p.moods,c.emotion_tags); genre=_genre_score(c,p); relationship=_match_count(p.relationship_focus,c.relationship_tags)
        req_signal=_required_signal_score(c,p); audience=_audience_score(c,p); tone=_match_count(p.tone_preferences,c.tone_tags)
        pace=_match_count(p.pace_preferences,c.pace_tags); surprise=_match_count([x for x in p.surprise_preferences if x!='fresh_premise'],c.surprise_tags)
        if 'fresh_premise' in p.surprise_preferences: surprise=max(surprise,0.8 if ('quirky' in c.tone_tags or 'worldbuilding' in c.surprise_tags) else 0.2)
        scene=_scene_fit(c,p); load=1.0 if p.cognitive_load and p.cognitive_load==c.cognitive_load else (0.0 if p.cognitive_load else 0.5)
        popularity=_pop_score(c,p); quality=0.5 if p.quality_preference!='acclaimed' else max(0.15,min(1.0,((c.rating_score or 5.2)-5)/4))
        freshness=0.5 if not c.release_year else max(0,min(1,(c.release_year-1990)/36))
        evidence=max(0.0,min(1.0,c.understanding_confidence or 0.35)); metadata=_metadata_quality(c)
        social=max(0.0,min(1.0,c.social_score))*max(0.0,min(1.0,c.social_confidence))
        features=[]
        if p.genres: features.append((genre,1.55))
        if p.required_signals: features.append((req_signal,1.55))
        if p.relationship_focus: features.append((relationship,1.35))
        if p.moods: features.append((mood,1.15))
        if p.tone_preferences: features.append((tone,1.0))
        if p.pace_preferences: features.append((pace,0.85))
        if p.surprise_preferences: features.append((surprise,0.8))
        if p.scene or p.companions: features.append((scene,1.0))
        if p.audience_preferences: features.append((audience,0.85))
        if p.cognitive_load: features.append((load,0.65))
        if p.popularity_preference: features.append((popularity,0.95))
        if p.quality_preference: features.append((quality,0.7))
        pref=(sum(v*w for v,w in features)/sum(w for _,w in features)) if features else 0.5
        penalty=_risk_penalty(c,p)
        # Social proof is deliberately weak: max ~5% contribution, never a hard gate.
        final=0.31*c.score+0.47*pref+0.08*evidence+0.06*metadata+0.03*freshness+0.05*social-penalty
        if p.exploration_mode=='explore':
            alpha=max(0.0,min(1.0,p.exploration_strength)); final=(1-alpha*0.20)*final+alpha*0.14*_novelty(c)+alpha*0.06*surprise
        elif p.exploration_mode=='balanced':
            alpha=max(0.0,min(1.0,p.exploration_strength)); final=(1-alpha*0.10)*final+alpha*0.07*_novelty(c)+alpha*0.03*surprise
        c.score=max(0.0,min(1.0,round(final,4)))
        c.score_breakdown.update({'rank_pref':round(pref,3),'rank_genre':round(genre,3),'rank_required_signal':round(req_signal,3),'rank_relationship':round(relationship,3),'rank_mood':round(mood,3),'rank_tone':round(tone,3),'rank_pace':round(pace,3),'rank_scene':round(scene,3),'rank_audience':round(audience,3),'rank_popularity':round(popularity,3),'rank_surprise':round(surprise,3),'rank_evidence':round(evidence,3),'rank_metadata':round(metadata,3),'rank_social':round(social,3),'risk_penalty':round(penalty,3),'exploration':round(p.exploration_strength,3)})
    ordered=sorted(cands,key=lambda x:x.score,reverse=True)
    dedup=[]; seen_titles=set()
    for c in ordered:
        key=' '.join(c.title.casefold().split())
        if key in seen_titles: continue
        seen_titles.add(key); dedup.append(c)
    ordered=dedup
    if p.exploration_mode=='precise': return ordered[:top_k]
    out=[]; strength=max(0.15,p.exploration_strength); remaining=ordered[:max(30,top_k*6)]
    while remaining and len(out)<top_k:
        best=None; best_score=-1
        for c in remaining:
            redundancy=max((_overlap(c,x) for x in out),default=0.0)
            adjusted=c.score-strength*0.15*redundancy+strength*0.05*_novelty(c)
            if adjusted>best_score: best_score=adjusted; best=c
        out.append(best); remaining.remove(best)
    return out
