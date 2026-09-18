from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Any

@dataclass
class EvidenceChunk:
    content_id: str
    evidence_type: str
    text: str
    source_type: str
    source_ref: str | None
    spoiler_level: str
    confidence: float

class EvidenceStore:
    def __init__(self, con: sqlite3.Connection):
        self.con = con

    def get(self, content_id: str, *, spoiler_tolerance: str = 'spoiler_free', limit: int = 8) -> list[EvidenceChunk]:
        try:
            rows = self.con.execute(
                """SELECT content_id,evidence_type,text,source_type,source_ref,spoiler_level,confidence
                   FROM content_evidence WHERE content_id=?
                   ORDER BY confidence DESC, evidence_type ASC""", (content_id,)
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        allowed = {'spoiler_free'} if spoiler_tolerance == 'spoiler_free' else {'spoiler_free','light_spoiler','full_spoiler'}
        out=[]
        for r in rows:
            d=dict(r) if hasattr(r,'keys') else {
                'content_id':r[0],'evidence_type':r[1],'text':r[2],'source_type':r[3],
                'source_ref':r[4],'spoiler_level':r[5],'confidence':r[6],
            }
            if d['spoiler_level'] not in allowed: continue
            out.append(EvidenceChunk(**d))
            if len(out)>=limit: break
        return out

    @staticmethod
    def summarize(chunks: list[EvidenceChunk]) -> dict[str, Any]:
        by_type={}
        for c in chunks:
            by_type.setdefault(c.evidence_type, []).append({
                'text':c.text,'source_type':c.source_type,'source_ref':c.source_ref,
                'spoiler_level':c.spoiler_level,'confidence':round(c.confidence,3),
            })
        return by_type
