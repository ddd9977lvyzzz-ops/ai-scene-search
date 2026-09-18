from __future__ import annotations
import json, sqlite3, argparse
from datetime import datetime, timezone

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--db',default='db/catalog.sqlite3');args=ap.parse_args()
    con=sqlite3.connect(args.db);con.row_factory=sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS content_evidence(evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,content_id TEXT NOT NULL,evidence_type TEXT NOT NULL,text TEXT NOT NULL,source_type TEXT NOT NULL,source_ref TEXT,spoiler_level TEXT NOT NULL DEFAULT 'spoiler_free',confidence REAL NOT NULL DEFAULT 0.5,created_at TEXT NOT NULL,UNIQUE(content_id,evidence_type,text))''')
    con.execute('CREATE INDEX IF NOT EXISTS idx_content_evidence_content ON content_evidence(content_id)');con.execute('DELETE FROM content_evidence')
    now=datetime.now(timezone.utc).isoformat()
    rows=con.execute('''SELECT c.content_id,c.title,c.overview,c.source,c.source_url,ci.spoiler_safe_summary,ci.risk_notes_json,ci.surprise_notes_json,ci.understanding_confidence FROM content c LEFT JOIN content_intelligence ci USING(content_id)''').fetchall()
    inserted=0
    for r in rows:
        conf=float(r['understanding_confidence'] or 0.45);items=[]
        if r['overview']:items.append(('official_or_catalog_summary',r['overview'].strip(),r['source'] or 'catalog',r['source_url'],'spoiler_free',min(.88,max(.45,conf))))
        if r['spoiler_safe_summary'] and r['spoiler_safe_summary'].strip()!=(r['overview'] or '').strip():items.append(('spoiler_safe_summary',r['spoiler_safe_summary'].strip(),'derived_content_intelligence',None,'spoiler_free',max(.35,conf-.05)))
        for raw,typ in [(r['risk_notes_json'],'risk_note'),(r['surprise_notes_json'],'surprise_note')]:
            try:vals=json.loads(raw or '[]')
            except Exception:vals=[]
            for x in vals[:6]:
                text=(x.get('text') or x.get('note') or x.get('label') or x.get('tag')) if isinstance(x,dict) else str(x)
                if text:items.append((typ,text.strip(),'derived_content_intelligence',None,'spoiler_free',max(.30,conf-.1)))
        for typ,text,source_type,source_ref,spoiler,score in items:
            cur=con.execute('INSERT OR IGNORE INTO content_evidence(content_id,evidence_type,text,source_type,source_ref,spoiler_level,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)',(r['content_id'],typ,text,source_type,source_ref,spoiler,score,now));inserted+=cur.rowcount
    con.commit();print({'content_rows':len(rows),'evidence_inserted':inserted,'evidence_total':con.execute('select count(*) from content_evidence').fetchone()[0]});con.close()
if __name__=='__main__':main()
