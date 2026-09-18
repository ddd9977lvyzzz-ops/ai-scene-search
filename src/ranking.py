from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from .models import Candidate, SceneProfile


INTERPRETABLE_DIMS = [
    'funny','light','relaxing','healing','romantic','exciting','tense',
    'thought_provoking','scary','fast','slow','romantic_rel','friendship',
    'family','sweet','gentle','realistic','bittersweet','dark','playful',
    'warm','niche','no_character_death','happy_ending','family_safe',
    'no_gore','no_jump_scares',
]


@dataclass
class RankBreakdown:
    structured: float = 0.0
    feature_vector: float = 0.0
    semantic: float = 0.0
    reference: float = 0.0
    quality: float = 0.0
    novelty: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.structured * 2.2
            + self.feature_vector * 2.4
            + self.semantic * 1.8
            + self.reference * 1.2
            + self.quality * 0.5
            + self.novelty * 0.35
        )


def _cosine(a: list[float], b: list[float]) -> float:
    dot=sum(x*y for x,y in zip(a,b))
    na=sqrt(sum(x*x for x in a)); nb=sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na and nb else 0.0


def _candidate_feature_set(c: Candidate) -> set[str]:
    s=set(c.emotion_tags+c.pace_tags+c.relationship_tags+c.tone_tags)
    if any(g.casefold()=='comedy' for g in c.genres): s.add('funny')
    if any(g.casefold()=='romance' for g in c.genres): s.add('romantic_rel')
    if c.popularity_bucket=='low': s.add('niche')
    for k,v in c.content_facts.items():
        if v is True: s.add(k)
    return s


def _profile_feature_set(p: SceneProfile) -> set[str]:
    s=set(p.moods+p.pace_preferences+p.relationship_focus+p.tone_preferences+p.required_facts)
    if 'funny' in p.required_signals: s.add('funny')
    if 'fast' in p.required_signals: s.add('fast')
    if 'Romance' in p.required_genres: s.add('romantic_rel')
    if p.popularity_preference=='niche': s.add('niche')
    return s


def feature_vector_score(c: Candidate, p: SceneProfile) -> float:
    cs=_candidate_feature_set(c); ps=_profile_feature_set(p)
    cv=[1.0 if d in cs else 0.0 for d in INTERPRETABLE_DIMS]
    pv=[1.0 if d in ps else 0.0 for d in INTERPRETABLE_DIMS]
    return _cosine(cv,pv)


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str,float]:
    """Fuse independent recall channels without forcing incomparable scores onto one scale."""
    scores: dict[str,float]={}
    for ranking in rankings:
        for i,content_id in enumerate(ranking, start=1):
            scores[content_id]=scores.get(content_id,0.0)+1.0/(k+i)
    return scores


def rank_candidate(
    c: Candidate,
    p: SceneProfile,
    *,
    semantic_score: float = 0.0,
    reference_score: float = 0.0,
    novelty_score: float = 0.0,
) -> RankBreakdown:
    structured=0.0
    if p.required_genres:
        structured+=sum(1 for g in p.required_genres if any(g.casefold() in x.casefold() for x in c.genres))/len(p.required_genres)
    if p.moods:
        structured+=len(set(p.moods)&set(c.emotion_tags))/len(p.moods)
    if p.relationship_focus:
        structured+=len(set(p.relationship_focus)&set(c.relationship_tags))/len(p.relationship_focus)
    if p.required_facts:
        structured+=len([f for f in p.required_facts if c.content_facts.get(f) is True])/len(p.required_facts)
    structured=min(1.0, structured/max(1, sum(bool(x) for x in [p.required_genres,p.moods,p.relationship_focus,p.required_facts])))

    quality=0.0
    if c.rating_score is not None:
        quality=max(0.0,min(1.0,(float(c.rating_score)-5.0)/5.0))
    quality=max(quality,c.understanding_confidence)

    return RankBreakdown(
        structured=structured,
        feature_vector=feature_vector_score(c,p),
        semantic=max(0.0,min(1.0,semantic_score)),
        reference=max(0.0,min(1.0,reference_score)),
        quality=max(0.0,min(1.0,quality)),
        novelty=max(0.0,min(1.0,novelty_score)),
    )
