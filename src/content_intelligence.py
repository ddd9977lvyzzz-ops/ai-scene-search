from __future__ import annotations
import json
import sqlite3
from typing import Any

def _j(value: str | None, fallback):
    try: return json.loads(value) if value else fallback
    except Exception: return fallback

class ContentIntelligenceIndex:
    def __init__(self, con: sqlite3.Connection):
        self.rows: dict[str, dict[str, Any]] = {}
        try: data = con.execute('SELECT * FROM content_intelligence').fetchall()
        except sqlite3.OperationalError: return
        for r in data:
            keys = r.keys() if hasattr(r, 'keys') else []
            d = dict(r) if keys else {}
            self.rows[d.get('content_id')] = {
                'tone_tags': _j(d.get('tone_tags_json'), []),
                'surprise_tags': _j(d.get('surprise_tags_json'), []),
                'content_facts': _j(d.get('content_facts_json'), {}),
                'risk_notes': _j(d.get('risk_notes_json'), []),
                'surprise_notes': _j(d.get('surprise_notes_json'), []),
                'popularity_bucket': d.get('popularity_bucket'),
                'understanding_confidence': float(d.get('understanding_confidence') or 0),
                'spoiler_safe_summary': d.get('spoiler_safe_summary') or '',
                'source_evidence': _j(d.get('source_evidence_json'), {}),
            }

    def get(self, content_id: str) -> dict[str, Any]:
        return self.rows.get(content_id, {})
