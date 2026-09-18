from __future__ import annotations
import argparse, json, sqlite3
from datetime import datetime, timezone

def j(v,fallback):
    try:return json.loads(v or '')
    except Exception:return fallback
def uniq(items):return list(dict.fromkeys(x for x in items if x))
def percentile_buckets(rows):
    by_type={}
    for r in rows:
        try:val=float(r['popularity'])
        except (TypeError,ValueError):continue
        by_type.setdefault(r['content_type'],[]).append(val)
    cuts={}
    for typ,vals in by_type.items():
        vals=sorted(vals)
        if len(vals)<8:continue
        def pct(p):return vals[min(len(vals)-1,max(0,int(round((len(vals)-1)*p))))]
        cuts[typ]=(pct(.33),pct(.75))
    return cuts
def bucket(pop,typ,cuts):
    try:v=float(pop)
    except (TypeError,ValueError):return 'unknown'
    if typ not in cuts:return 'unknown'
    low,high=cuts[typ]
    return 'low' if v<=low else ('high' if v>=high else 'medium')
def infer(row,pop_bucket):
    title=row['title'] or ''; overview=row['overview'] or ''; text=f'{title} {overview}'.casefold()
    genres=[x.casefold() for x in j(row['genres_json'],[])]; emotions=j(row['emotion_tags_json'],[]); relationships=j(row['relationship_tags_json'],[]); themes=j(row['theme_tags_json'],[]); risks=j(row['risk_tags_json'],[]); pace=j(row['pace_tags_json'],[])
    tones=[]
    if 'romantic' in relationships or 'romance' in genres:tones.append('romantic')
    if any(x in genres for x in ['comedy','family']) or 'funny' in emotions:tones.extend(['playful','warm'])
    if 'romantic' in relationships and ('comedy' in genres or 'funny' in emotions):tones.append('sweet')
    if any(x in text for x in ['quiet','gentle','slice of life','日常','温柔','平静']):tones.append('gentle')
    if any(x in genres for x in ['crime','horror','thriller','war']) or 'tense' in emotions:tones.append('dark')
    if any(x in text for x in ['realistic','real life','现实','写实']):tones.append('realistic')
    if 'emotionally_heavy' in risks and 'romantic' in relationships:tones.append('bittersweet')
    if any(x in text for x in ['quirky','offbeat','absurd','怪诞','古怪']):tones.append('quirky')
    surprises=[]
    if any(x in genres for x in ['mystery','thriller','crime']) or any(x in text for x in ['secret','mystery','truth','conspiracy','谜','真相']):surprises.append('plot_reveal')
    if any(x in genres for x in ['science-fiction','sci-fi','fantasy','supernatural']) or any(x in text for x in ['future','magic','supernatural','未来','魔法']):surprises.append('worldbuilding')
    if 'romantic' in relationships:surprises.append('relationship_turns')
    if 'comedy' in genres or 'funny' in emotions:surprises.append('comic_payoff')
    if any(x in genres for x in ['action','adventure']):surprises.append('visual_set_piece')
    if row['content_type']=='documentary':surprises.append('insight')
    risk_notes=[{'tag':tag,'confidence':0.72,'evidence':'available genre/summary metadata + deterministic rule','spoiler_level':'none'} for tag in risks]
    surprise_notes=[{'tag':tag,'confidence':0.62,'evidence':'genre/overview pattern; describes surprise dimension, not a specific plot event','spoiler_level':'none'} for tag in uniq(surprises)]
    overview_len=len(overview); base=.38+(.16 if overview_len>80 else .08 if overview_len>20 else 0)+(.12 if genres else 0)+(.08 if relationships else 0)+(.08 if risks else 0); confidence=min(.9,base)
    central=[]
    if 'romantic' in relationships:central.append('romantic relationship')
    if 'family' in relationships:central.append('family relationship')
    if 'friendship' in relationships:central.append('friendship')
    facts={'central_relationships':central,'themes':themes[:8],'watching_experience':uniq([*emotions,*pace])[:10],'known_limits':'Derived from available synopsis/genre metadata. Specific scene-level triggers require richer licensed evidence.'}
    provenance=j(row['tag_provenance_json'],{}); evidence={'canonical_source':row['source'],'source_url':row['source_url'],'method':'deterministic_content_intelligence_v1','metadata_layer_method':provenance.get('method','source_or_rule_metadata'),'metadata_layer_note':provenance.get('note')}
    return uniq(tones),uniq(surprises),facts,risk_notes,surprise_notes,round(confidence,3),evidence
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--db',default='db/catalog.sqlite3');args=ap.parse_args()
    con=sqlite3.connect(args.db);con.row_factory=sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS content_intelligence(content_id TEXT PRIMARY KEY,schema_version TEXT NOT NULL,spoiler_safe_summary TEXT,tone_tags_json TEXT NOT NULL,surprise_tags_json TEXT NOT NULL,content_facts_json TEXT NOT NULL,risk_notes_json TEXT NOT NULL,surprise_notes_json TEXT NOT NULL,popularity_bucket TEXT,understanding_confidence REAL NOT NULL,source_evidence_json TEXT NOT NULL,updated_at TEXT NOT NULL)''')
    rows=con.execute('SELECT * FROM content').fetchall();cuts=percentile_buckets(rows);payload=[];now=datetime.now(timezone.utc).isoformat()
    for r in rows:
        pb=bucket(r['popularity'],r['content_type'],cuts);tones,surprises,facts,risk_notes,surprise_notes,conf,evidence=infer(r,pb);summary=(r['overview'] or '').strip()
        if len(summary)>420:summary=summary[:417].rsplit(' ',1)[0]+'…'
        payload.append((r['content_id'],'1.0',summary,json.dumps(tones,ensure_ascii=False),json.dumps(surprises,ensure_ascii=False),json.dumps(facts,ensure_ascii=False),json.dumps(risk_notes,ensure_ascii=False),json.dumps(surprise_notes,ensure_ascii=False),pb,conf,json.dumps(evidence,ensure_ascii=False),now))
    con.executemany('INSERT OR REPLACE INTO content_intelligence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',payload)
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",('content_intelligence_version','1.0'));con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",('content_intelligence_count',str(len(payload))))
    con.commit();con.close();print(json.dumps({'content_intelligence':len(payload),'schema_version':'1.0'},ensure_ascii=False))
if __name__=='__main__':main()
