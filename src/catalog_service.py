from __future__ import annotations
import json
import sqlite3
from typing import Any

def _j(value: str | None, fallback=None):
    if fallback is None: fallback=[]
    try: return json.loads(value) if value else fallback
    except Exception: return fallback

def _int(value):
    try: return int(value)
    except Exception: return None

class CatalogService:
    def __init__(self, db_path: str):
        self.con = sqlite3.connect(db_path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row

    def count(self) -> int:
        return int(self.con.execute('SELECT COUNT(*) FROM content').fetchone()[0])

    def content_types(self) -> list[dict[str, Any]]:
        rows = self.con.execute('SELECT content_type, COUNT(*) AS n FROM content GROUP BY content_type ORDER BY n DESC').fetchall()
        return [{'content_type': r['content_type'], 'count': int(r['n'])} for r in rows]

    def _intelligence(self, content_id: str) -> dict[str, Any]:
        try: r=self.con.execute('SELECT * FROM content_intelligence WHERE content_id=?',(content_id,)).fetchone()
        except sqlite3.OperationalError: return {}
        if not r: return {}
        return {
            'tone_tags':_j(r['tone_tags_json']), 'surprise_tags':_j(r['surprise_tags_json']),
            'content_facts':_j(r['content_facts_json'],{}), 'risk_notes':_j(r['risk_notes_json']),
            'surprise_notes':_j(r['surprise_notes_json']), 'popularity_bucket':r['popularity_bucket'],
            'understanding_confidence':float(r['understanding_confidence'] or 0),
            'spoiler_safe_summary':r['spoiler_safe_summary'] or '', 'source_evidence':_j(r['source_evidence_json'],{}),
        }

    def _serialize(self, r: sqlite3.Row, include_description: bool = True) -> dict[str, Any]:
        runtime = _int(r['runtime_minutes']) or _int(r['episode_runtime_minutes']); intel=self._intelligence(r['content_id'])
        item = {
            'content_id': r['content_id'], 'title': r['title'], 'original_title': r['original_title'],
            'aliases': _j(r['aliases_json']), 'content_type': r['content_type'], 'release_year': _int(r['release_year']),
            'runtime_minutes': runtime, 'episode_runtime_minutes': _int(r['episode_runtime_minutes']),
            'countries': _j(r['countries_json']), 'language': r['language'], 'genres': _j(r['genres_json']),
            'poster_url': r['poster_url'] or None, 'backdrop_url': r['backdrop_url'] or None,
            'origin_platforms': _j(r['origin_platforms_json']), 'platforms': _j(r['origin_platforms_json']),
            'cast': _j(r['cast_json']), 'directors': _j(r['directors_json']), 'creators': _j(r['creators_json']),
            'source': r['source'], 'source_id': r['source_id'], 'source_url': r['source_url'],
            'scene_tags': _j(r['scene_tags_json']), 'emotion_tags': _j(r['emotion_tags_json']),
            'watching_tags': _j(r['watching_tags_json']), 'audience_tags': _j(r['audience_tags_json']),
            'pace_tags': _j(r['pace_tags_json']), 'risk_tags': _j(r['risk_tags_json']),
            'relationship_tags': _j(r['relationship_tags_json']), 'theme_tags': _j(r['theme_tags_json']),
            'cognitive_load': r['cognitive_load'], 'tag_confidence': r['tag_confidence'],
            'rating_score': r['rating_score'], 'data_quality_score': r['data_quality_score'],
            'tone_tags':intel.get('tone_tags',[]), 'surprise_tags':intel.get('surprise_tags',[]),
            'popularity_bucket':intel.get('popularity_bucket'), 'understanding_confidence':intel.get('understanding_confidence',0),
        }
        if include_description:
            item['description'] = r['overview'] or ''; item['tag_provenance'] = _j(r['tag_provenance_json'],{})
            item['platform_evidence'] = _j(r['platform_evidence_json'],{}); item['content_facts']=intel.get('content_facts',{})
            item['risk_notes']=intel.get('risk_notes',[]); item['surprise_notes']=intel.get('surprise_notes',[])
            item['spoiler_safe_summary']=intel.get('spoiler_safe_summary',''); item['source_evidence']=intel.get('source_evidence',{})
        return item

    def quality_stats(self) -> dict[str, Any]:
        total=self.count()
        poster=int(self.con.execute("SELECT COUNT(*) FROM content WHERE poster_url IS NOT NULL AND TRIM(poster_url)<>''").fetchone()[0])
        desc=int(self.con.execute("SELECT COUNT(*) FROM content WHERE overview IS NOT NULL AND TRIM(overview)<>''").fetchone()[0])
        try: vectors=int(self.con.execute('SELECT COUNT(*) FROM content_vectors').fetchone()[0])
        except Exception: vectors=0
        try: intel=int(self.con.execute('SELECT COUNT(*) FROM content_intelligence').fetchone()[0])
        except Exception: intel=0
        try: evidence=int(self.con.execute('SELECT COUNT(*) FROM content_evidence').fetchone()[0])
        except Exception: evidence=0
        platform_rows=int(self.con.execute("SELECT COUNT(*) FROM content WHERE origin_platforms_json IS NOT NULL AND origin_platforms_json<>'[]'").fetchone()[0])
        movie_total=int(self.con.execute("SELECT COUNT(*) FROM content WHERE content_type='movie'").fetchone()[0])
        movie_genre=int(self.con.execute("SELECT COUNT(*) FROM content WHERE content_type='movie' AND lower(genres_json) NOT IN ('["film"]','[]')").fetchone()[0])
        meta={}
        try: meta={r[0]:r[1] for r in self.con.execute('SELECT key,value FROM catalog_meta').fetchall()}
        except Exception: pass
        return {
            'records': total, 'poster_coverage': round(poster/max(total,1),4), 'description_coverage': round(desc/max(total,1),4),
            'vectors': vectors, 'embedding_coverage': round(vectors/max(total,1),4), 'content_intelligence':intel,
            'content_intelligence_coverage':round(intel/max(total,1),4), 'evidence_chunks':evidence,
            'platform_evidence_records':platform_rows, 'platform_evidence_coverage':round(platform_rows/max(total,1),4),
            'movie_records':movie_total, 'movie_genre_enriched':movie_genre, 'movie_genre_coverage':round(movie_genre/max(movie_total,1),4),
            'embedding_dim':int(meta.get('embedding_dim','0') or 0), 'tag_rule_version':meta.get('tag_rule_version'),
            'curated_movie_enrichment_count':int(meta.get('curated_movie_enrichment_count','0') or 0),
            'china_series': int(self.con.execute("""SELECT COUNT(*) FROM content WHERE content_type='series' AND
                (countries_json LIKE '%中国大陆%' OR language IN ('中文','Chinese','Mandarin','Cantonese'))""").fetchone()[0]),
        }

    def browse(self, content_type: str | None = None, limit: int = 18, offset: int = 0) -> list[dict[str, Any]]:
        limit=max(1,min(60,int(limit))); offset=max(0,int(offset))
        if content_type:
            rows=self.con.execute('SELECT * FROM content WHERE content_type=? ORDER BY COALESCE(release_year,0) DESC,title COLLATE NOCASE ASC LIMIT ? OFFSET ?',(content_type,limit,offset)).fetchall()
        else:
            rows=self.con.execute('SELECT * FROM content ORDER BY COALESCE(release_year,0) DESC,title COLLATE NOCASE ASC LIMIT ? OFFSET ?',(limit,offset)).fetchall()
        return [self._serialize(r,False) for r in rows]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        q=(query or '').strip()
        if not q: return []
        limit=max(1,min(40,int(limit))); like=f'%{q}%'
        rows=self.con.execute('SELECT * FROM content WHERE title LIKE ? COLLATE NOCASE OR overview LIKE ? COLLATE NOCASE OR search_text LIKE ? COLLATE NOCASE ORDER BY CASE WHEN title LIKE ? COLLATE NOCASE THEN 0 ELSE 1 END,COALESCE(release_year,0) DESC LIMIT ?',(like,like,like,like,limit)).fetchall()
        return [self._serialize(r,False) for r in rows]

    def get(self, content_id: str) -> dict[str, Any] | None:
        row=self.con.execute('SELECT * FROM content WHERE content_id=?',(content_id,)).fetchone()
        return self._serialize(row,True) if row else None
