from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import joblib
import numpy as np

from .content_intelligence import ContentIntelligenceIndex
from .models import Candidate, SceneProfile
from .ranking import feature_vector_score, reciprocal_rank_fusion


def _j(value):
    try: return json.loads(value or "[]")
    except Exception: return []


def _int(value):
    try: return int(value)
    except Exception: return None


def _float(value):
    try: return float(value)
    except Exception: return None


GENRE_CANONICAL_TERMS = {
    'Romance': ['romance', 'romantic', 'love story', 'relationship'],
    'Comedy': ['comedy', 'funny', 'humor'],
    'Thriller': ['thriller', 'suspense', 'tense'],
    'Mystery': ['mystery', 'detective', 'puzzle'],
    'Crime': ['crime', 'detective'],
    'Action': ['action', 'fight', 'mission'],
    'Horror': ['horror', 'scary', 'fear'],
    'Sci-Fi': ['science fiction', 'sci-fi', 'future'],
    'Fantasy': ['fantasy', 'magic'],
    'Adventure': ['adventure', 'journey'],
    'Family': ['family'],
    'Coming-of-age': ['coming of age', 'youth'],
    'Music': ['music'],
}


class CatalogRetriever:
    """Hybrid retrieval over structured constraints, sparse FTS and semantic vectors.

    Explicit user constraints are not delegated to embeddings. Dense retrieval generates
    candidates; required genres/runtimes/risks remain structured and inspectable.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.con = sqlite3.connect(db_path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.intelligence = ContentIntelligenceIndex(self.con)
        self.verified_platforms = {}
        try:
            for row in self.con.execute("SELECT content_id,platform FROM platform_availability WHERE status='available' AND confidence>=0.75"):
                self.verified_platforms.setdefault(row['content_id'], []).append(row['platform'])
        except sqlite3.OperationalError:
            pass
        self.vectors = {}
        try:
            for row in self.con.execute("SELECT content_id,vector_json FROM content_vectors"):
                self.vectors[row["content_id"]] = np.asarray(json.loads(row["vector_json"]), dtype=np.float32)
        except sqlite3.OperationalError:
            pass
        model_path = Path(db_path).with_name("embedding_model.joblib")
        self.embedding_model = None
        if model_path.exists():
            loaded = joblib.load(model_path)
            self.embedding_model = loaded["model"] if isinstance(loaded, dict) else loaded

    def _from_row(self, row):
        intel = self.intelligence.get(row["content_id"])
        return Candidate(
            content_id=row["content_id"], title=row["title"], content_type=row["content_type"],
            release_year=_int(row["release_year"]),
            runtime_minutes=_int(row["runtime_minutes"]) or _int(row["episode_runtime_minutes"]),
            genres=_j(row["genres_json"]), description=row["overview"] or "",
            scene_tags=_j(row["scene_tags_json"]), emotion_tags=_j(row["emotion_tags_json"]),
            watching_tags=_j(row["watching_tags_json"]), risk_tags=_j(row["risk_tags_json"]),
            cognitive_load=row["cognitive_load"], platforms=self.verified_platforms.get(row["content_id"], []), poster_url=row["poster_url"],
            audience_tags=_j(row["audience_tags_json"]), pace_tags=_j(row["pace_tags_json"]),
            relationship_tags=_j(row["relationship_tags_json"]), theme_tags=_j(row["theme_tags_json"]),
            tone_tags=intel.get('tone_tags', []), surprise_tags=intel.get('surprise_tags', []),
            content_facts=intel.get('content_facts', {}), risk_notes=intel.get('risk_notes', []),
            surprise_notes=intel.get('surprise_notes', []), popularity_value=_float(row["popularity"]),
            popularity_bucket=intel.get('popularity_bucket'), rating_score=_float(row["rating_score"]),
            understanding_confidence=float(intel.get('understanding_confidence', 0.0)),
        )

    @staticmethod
    def _genre_sql(genre: str) -> tuple[str, list[str]]:
        g = genre.casefold()
        if g == 'romance':
            return "(lower(genres_json) LIKE ? OR relationship_tags_json LIKE '%\"romantic\"%')", ['%romance%']
        if g == 'sci-fi':
            return "(lower(genres_json) LIKE ? OR lower(genres_json) LIKE ?)", ['%sci-fi%', '%science-fiction%']
        if g == 'thriller':
            return "(lower(genres_json) LIKE ? OR lower(genres_json) LIKE ?)", ['%thriller%', '%suspense%']
        return "lower(genres_json) LIKE ?", [f'%{g}%']

    def _structured_rows(self, profile: SceneProfile, exclude_ids: list[str]):
        where, params = ["1=1"], []
        if profile.content_types:
            where.append(f"content_type IN ({','.join('?' for _ in profile.content_types)})"); params.extend(profile.content_types)
        if profile.runtime_max is not None:
            where.append("COALESCE(runtime_minutes,episode_runtime_minutes) IS NOT NULL")
            where.append("COALESCE(runtime_minutes,episode_runtime_minutes)<=?"); params.append(profile.runtime_max)
        if profile.year_min is not None:
            where.append("release_year IS NOT NULL AND release_year>=?"); params.append(profile.year_min)
        if profile.language == 'Chinese':
            where.append("(language IN ('中文','Chinese','Mandarin','Cantonese') OR countries_json LIKE '%中国大陆%')")

        for genre in profile.required_genres:
            clause, gp = self._genre_sql(genre)
            where.append(clause); params.extend(gp)

        for signal in profile.required_signals:
            if signal == 'funny':
                where.append("(lower(genres_json) LIKE '%comedy%' OR emotion_tags_json LIKE '%\"funny\"%' OR audience_tags_json LIKE '%\"comedy\"%')")
            elif signal == 'fast':
                where.append("(pace_tags_json LIKE '%\"fast\"%' OR emotion_tags_json LIKE '%\"exciting\"%' OR lower(genres_json) LIKE '%action%' OR lower(genres_json) LIKE '%thriller%' OR lower(genres_json) LIKE '%adventure%')")

        for genre in profile.avoid_genres:
            clause, gp = self._genre_sql(genre)
            where.append(f"NOT {clause}"); params.extend(gp)
        for risk in profile.avoid_risks:
            where.append("risk_tags_json NOT LIKE ?"); params.append(f'%"{risk}"%')
        if profile.platforms:
            clauses=[]
            for platform in profile.platforms:
                clauses.append("origin_platforms_json LIKE ?"); params.append(f'%{platform}%')
            where.append("("+" OR ".join(clauses)+")")
        if exclude_ids:
            where.append(f"content_id NOT IN ({','.join('?' for _ in exclude_ids)})"); params.extend(exclude_ids)
        return self.con.execute(f"SELECT * FROM content WHERE {' AND '.join(where)}", params).fetchall()

    @staticmethod
    def _semantic_terms(profile: SceneProfile) -> list[str]:
        terms: list[str] = []
        for genre in [*profile.required_genres, *profile.genres]:
            terms.extend(GENRE_CANONICAL_TERMS.get(genre, [genre.casefold()]))
        terms.extend(profile.relationship_focus)
        terms.extend(profile.required_signals)
        terms.extend(profile.audience_preferences)
        terms.extend(profile.moods)
        terms.extend(profile.tone_preferences)
        terms.extend(profile.pace_preferences)
        terms.extend(profile.surprise_preferences)
        terms.extend(profile.required_facts)
        if profile.cognitive_load: terms.append(f'{profile.cognitive_load} cognitive load')
        if profile.popularity_preference == 'niche': terms.extend(['niche', 'less mainstream', 'hidden gem'])
        if profile.popularity_preference == 'mainstream': terms.extend(['popular', 'mainstream'])
        if profile.quality_preference == 'acclaimed': terms.extend(['acclaimed', 'highly rated'])
        return list(dict.fromkeys(x for x in terms if x))

    def _fts_scores(self, profile: SceneProfile) -> dict[str, float]:
        terms = self._semantic_terms(profile)[:24]
        terms = [re.sub(r'[^a-zA-Z0-9_-]+', ' ', t).strip() for t in terms]
        terms = [t for t in terms if len(t) >= 2]
        if not terms: return {}
        match = " OR ".join('"'+t.replace('"','')+'"' for t in terms)
        try:
            rows = self.con.execute(
                "SELECT content_id,bm25(content_fts) score FROM content_fts WHERE content_fts MATCH ? LIMIT 700",
                (match,),
            ).fetchall()
            if not rows: return {}
            raw = {r["content_id"]: abs(float(r["score"])) for r in rows}
            vals = list(raw.values()); lo, hi = min(vals), max(vals); span=max(hi-lo,1e-9)
            return {k: (v-lo)/span for k,v in raw.items()}
        except sqlite3.OperationalError:
            return {}

    @staticmethod
    def _popularity_match(c: Candidate, profile: SceneProfile) -> float:
        if not profile.popularity_preference: return 0.5
        bucket = c.popularity_bucket or 'unknown'
        if profile.popularity_preference == 'niche':
            return {'low': 1.0, 'medium': 0.72, 'unknown': 0.58, 'high': 0.12}.get(bucket, 0.5)
        if profile.popularity_preference == 'mainstream':
            return {'high': 1.0, 'medium': 0.72, 'unknown': 0.45, 'low': 0.18}.get(bucket, 0.5)
        return 0.5

    @staticmethod
    def _quality_match(c: Candidate, profile: SceneProfile) -> float:
        if profile.quality_preference != 'acclaimed': return 0.5
        if c.rating_score is None: return 0.35
        return max(0.0, min(1.0, (c.rating_score - 5.0) / 4.0))

    @classmethod
    def _structured_match(cls, c: Candidate, p: SceneProfile) -> tuple[float, dict[str,float]]:
        parts: dict[str, float] = {}
        if p.content_types: parts['type'] = 1.0 if c.content_type in p.content_types else 0.0
        if p.genres:
            matched = sum(any(g.casefold() in cg.casefold() or cg.casefold() in g.casefold() for cg in c.genres) for g in p.genres)
            if 'Romance' in p.genres and 'romantic' in c.relationship_tags: matched = max(matched, 1)
            parts['genre'] = min(1.0, matched/max(1,len(p.genres)))
        if p.relationship_focus:
            parts['relationship'] = len(set(p.relationship_focus)&set(c.relationship_tags))/max(1,len(p.relationship_focus))
        if p.required_signals:
            hits=0
            for signal in p.required_signals:
                if signal=='funny' and ('funny' in c.emotion_tags or any('comedy' in g.casefold() for g in c.genres) or 'playful' in c.tone_tags): hits+=1
                elif signal=='fast' and ('fast' in c.pace_tags or 'exciting' in c.emotion_tags or any(g.casefold() in {'action','adventure','thriller'} for g in c.genres)): hits+=1
            parts['required_signal'] = hits/max(1,len(p.required_signals))
        if p.audience_preferences:
            hits=len(set(p.audience_preferences)&set(c.audience_tags))
            if 'adult' in p.audience_preferences and 'kids' not in c.audience_tags: hits=max(hits,0.55)
            if 'family' in p.audience_preferences and ('family' in c.audience_tags or any('family' in g.casefold() for g in c.genres)): hits=max(hits,1.0)
            parts['audience'] = min(1.0,hits/max(1,len(p.audience_preferences)))
        if p.moods: parts['mood'] = len(set(p.moods)&set(c.emotion_tags))/max(1,len(p.moods))
        if p.tone_preferences: parts['tone'] = len(set(p.tone_preferences)&set(c.tone_tags))/max(1,len(p.tone_preferences))
        if p.pace_preferences: parts['pace'] = len(set(p.pace_preferences)&set(c.pace_tags))/max(1,len(p.pace_preferences))
        if p.surprise_preferences: parts['surprise'] = len(set(p.surprise_preferences)&set(c.surprise_tags))/max(1,len(p.surprise_preferences))
        if p.required_facts: parts['plot_fact'] = sum(1 for f in p.required_facts if c.content_facts.get(f) is True)/max(1,len(p.required_facts))
        if p.scene: parts['scene'] = 1.0 if p.scene in c.scene_tags else 0.0
        if p.companions: parts['companions'] = 1.0 if p.companions in c.scene_tags else 0.0
        if p.cognitive_load: parts['cognitive'] = 1.0 if p.cognitive_load == c.cognitive_load else 0.0
        if p.popularity_preference: parts['popularity'] = cls._popularity_match(c,p)
        if p.quality_preference: parts['quality'] = cls._quality_match(c,p)
        weights={'type':1.0,'genre':1.6,'relationship':1.35,'required_signal':1.5,'audience':0.75,'mood':1.15,'tone':1.05,'pace':0.75,'surprise':0.8,'scene':0.65,'companions':0.6,'cognitive':0.75,'popularity':1.0,'quality':0.7}
        if not parts: return 0.5, parts
        total=sum(parts[k]*weights.get(k,1) for k in parts); denom=sum(weights.get(k,1) for k in parts)
        return total/max(denom,1e-9), parts

    def _anchor_candidate(self, profile: SceneProfile):
        ref=(profile.source_reference or '').strip()
        if not ref: return None
        row=self.con.execute("SELECT * FROM content WHERE title=? COLLATE NOCASE OR original_title=? COLLATE NOCASE ORDER BY data_quality_score DESC LIMIT 1",(ref,ref)).fetchone()
        if row is None:
            row=self.con.execute("SELECT * FROM content WHERE title LIKE ? COLLATE NOCASE OR aliases_json LIKE ? COLLATE NOCASE ORDER BY data_quality_score DESC LIMIT 1",(f'%{ref}%',f'%{ref}%')).fetchone()
        return self._from_row(row) if row else None

    @staticmethod
    def _anchor_similarity(c: Candidate, anchor: Candidate | None) -> float:
        if anchor is None: return 0.0
        a=set(x.casefold() for x in [*anchor.genres,*anchor.emotion_tags,*anchor.relationship_tags,*anchor.theme_tags,*anchor.tone_tags,*anchor.pace_tags])
        b=set(x.casefold() for x in [*c.genres,*c.emotion_tags,*c.relationship_tags,*c.theme_tags,*c.tone_tags,*c.pace_tags])
        if not a or not b: return 0.0
        return len(a&b)/max(1,len(a|b))

    def retrieve(self, query: str, profile: SceneProfile, limit: int = 100, exclude_ids: list[str] | None = None):
        anchor=self._anchor_candidate(profile)
        effective_excludes=list(exclude_ids or [])
        if anchor and anchor.content_id not in effective_excludes: effective_excludes.append(anchor.content_id)
        rows = self._structured_rows(profile, effective_excludes)
        fts = self._fts_scores(profile)
        semantic_terms = self._semantic_terms(profile)
        query_text = " ".join([query, *semantic_terms]).strip()
        query_vector = None
        if self.embedding_model is not None and query_text:
            query_vector = np.asarray(self.embedding_model.transform([query_text])[0], dtype=np.float32)
            if anchor is not None:
                av=self.vectors.get(anchor.content_id)
                if av is not None and len(av)==len(query_vector):
                    query_vector=0.58*query_vector+0.42*av
                    norm=float(np.linalg.norm(query_vector))
                    if norm>1e-9: query_vector=query_vector/norm

        raw_title_terms = re.findall(r'[A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,8}', query)
        candidates=[]
        for row in rows:
            c=self._from_row(row); hay=(row["search_text"] or "").casefold(); lexical=fts.get(c.content_id,0.0)
            direct_hits=sum(1 for token in raw_title_terms if token.casefold() in hay)
            lexical=min(1.0, lexical + min(0.18, direct_hits*0.04))
            structured, parts = self._structured_match(c, profile)
            vector_score=0.0; vector=self.vectors.get(c.content_id)
            if query_vector is not None and vector is not None and len(vector)==len(query_vector):
                vector_score=max(0.0,float(np.dot(query_vector,vector)))
            evidence_quality=max(0.0,min(1.0,c.understanding_confidence or 0.45))
            anchor_score=self._anchor_similarity(c,anchor)
            scene_vector=feature_vector_score(c,profile)
            if anchor is None:
                c.score=max(0.0,min(1.0,0.12*lexical+0.28*vector_score+0.34*structured+0.18*scene_vector+0.08*evidence_quality))
            else:
                c.score=max(0.0,min(1.0,0.10*lexical+0.25*vector_score+0.31*structured+0.16*scene_vector+0.10*anchor_score+0.08*evidence_quality))
            c.score_breakdown={"sparse":round(lexical,3),"semantic_vector":round(vector_score,3),"scene_vector":round(scene_vector,3),"structured":round(structured,3),"anchor":round(anchor_score,3),"evidence_quality":round(evidence_quality,3),**{f'f_{k}':round(v,3) for k,v in parts.items()}}
            if profile.required_genres: c.retrieval_reasons.append('explicit_genre_gate')
            if profile.required_signals: c.retrieval_reasons.append('explicit_signal_gate')
            if semantic_terms: c.retrieval_reasons.append('canonical_semantic_query')
            if anchor is not None: c.retrieval_reasons.append('reference_title_similarity')
            candidates.append(c)
        if candidates:
            channel_rankings = []
            for key in ('sparse','semantic_vector','scene_vector','structured'):
                ordered=sorted(candidates,key=lambda x:x.score_breakdown.get(key,0.0),reverse=True)
                channel_rankings.append([x.content_id for x in ordered])
            if anchor is not None:
                ordered=sorted(candidates,key=lambda x:x.score_breakdown.get('anchor',0.0),reverse=True)
                channel_rankings.append([x.content_id for x in ordered])
            rrf=reciprocal_rank_fusion(channel_rankings,k=60)
            max_rrf=max(rrf.values()) if rrf else 1.0
            for cand in candidates:
                rrf_norm=rrf.get(cand.content_id,0.0)/max_rrf
                cand.score=max(0.0,min(1.0,0.72*cand.score+0.28*rrf_norm))
                cand.score_breakdown['rrf']=round(rrf_norm,3)
                cand.retrieval_reasons.append('rrf_multi_channel_fusion')
        candidates.sort(key=lambda c:c.score,reverse=True)
        return candidates[:limit]
