from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone


DDL = """
CREATE TABLE IF NOT EXISTS platform_availability(
    content_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'CN',
    status TEXT NOT NULL,
    source_url TEXT,
    source_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    checked_at TEXT NOT NULL,
    PRIMARY KEY(content_id, platform, region)
);
CREATE INDEX IF NOT EXISTS idx_platform_availability_lookup
ON platform_availability(platform, region, status, confidence);
"""


def _j(value):
    try:
        return json.loads(value or '[]')
    except Exception:
        return []


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--db',default='db/catalog.sqlite3')
    args=ap.parse_args()

    con=sqlite3.connect(args.db)
    con.row_factory=sqlite3.Row
    con.executescript(DDL)
    now=datetime.now(timezone.utc).isoformat()

    rows=con.execute("""
        SELECT content_id,title,origin_platforms_json,source,source_url
        FROM content
    """).fetchall()

    payload=[]
    for r in rows:
        source=(r['source'] or '').lower()
        for platform in _j(r['origin_platforms_json']):
            # Origin metadata is useful context but is NOT automatically treated as current availability.
            status='origin_only'
            confidence=.42
            source_type='origin_metadata'

            # Curated official platform pages are allowed to become hard availability evidence.
            if source=='iqiyi_curated' and platform=='iqiyi':
                status='available'
                confidence=.98
                source_type='official_title_page'

            payload.append((
                r['content_id'],platform,'CN',status,r['source_url'],source_type,confidence,now
            ))

    con.executemany("""
        INSERT OR REPLACE INTO platform_availability
        (content_id,platform,region,status,source_url,source_type,confidence,checked_at)
        VALUES (?,?,?,?,?,?,?,?)
    """,payload)
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",('platform_availability_version','1.0'))
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",('verified_platform_rows',str(sum(1 for x in payload if x[3]=='available'))))
    con.commit()
    print(json.dumps({
        'rows':len(payload),
        'verified_available':sum(1 for x in payload if x[3]=='available'),
        'policy':'origin_only != available; explicit platform queries require verified available evidence'
    },ensure_ascii=False,indent=2))
    con.close()


if __name__=='__main__':
    main()
