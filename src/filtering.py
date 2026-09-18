from __future__ import annotations
from .models import Candidate, SceneProfile


def _genre_match(candidate: Candidate, genre: str) -> bool:
    g=genre.casefold()
    if g=='romance' and 'romantic' in candidate.relationship_tags:
        return True
    if g=='sci-fi':
        return any(x.casefold() in {'sci-fi','science-fiction','science fiction'} for x in candidate.genres)
    return any(g in x.casefold() or x.casefold() in g for x in candidate.genres)



def _signal_match(candidate: Candidate, signal: str) -> bool:
    if signal == 'funny':
        return ('funny' in candidate.emotion_tags or 'playful' in candidate.tone_tags or
                any('comedy' in g.casefold() for g in candidate.genres))
    if signal == 'fast':
        return ('fast' in candidate.pace_tags or 'exciting' in candidate.emotion_tags or
                any(g.casefold() in {'action','adventure','thriller'} for g in candidate.genres))
    return True


def hard_filter(cands:list[Candidate], p:SceneProfile):
    """Deterministic gate. Exploration is never allowed to bypass this function."""
    kept=[]; dropped=[]
    for c in cands:
        reasons=[]
        if p.runtime_max is not None and c.runtime_minutes is not None and c.runtime_minutes>p.runtime_max:
            reasons.append(f'runtime>{p.runtime_max}')
        if p.year_min is not None and c.release_year is not None and c.release_year<p.year_min:
            reasons.append(f'year<{p.year_min}')
        if p.content_types and c.content_type not in p.content_types:
            reasons.append('content_type_mismatch')
        for required in p.required_genres:
            if not _genre_match(c, required): reasons.append(f'required_genre_missing:{required}')
        for signal in p.required_signals:
            if not _signal_match(c, signal): reasons.append(f'required_signal_missing:{signal}')
        for avoid in p.avoid_genres:
            if _genre_match(c, avoid): reasons.append(f'avoid_genre:{avoid}')
        if p.avoid_risks and any(r in c.risk_tags for r in p.avoid_risks):
            reasons.extend([f'avoid_risk:{r}' for r in p.avoid_risks if r in c.risk_tags])
        for fact in p.required_facts:
            if c.content_facts.get(fact) is not True:
                reasons.append(f'required_fact_missing:{fact}')
        for fact in p.avoid_facts:
            if c.content_facts.get(fact) is True:
                reasons.append(f'avoid_fact:{fact}')
        if p.platforms and not set(p.platforms)&set(c.platforms):
            reasons.append('platform_unavailable_in_snapshot')
        if reasons: dropped.append((c,reasons))
        else: kept.append(c)
    return kept,dropped
