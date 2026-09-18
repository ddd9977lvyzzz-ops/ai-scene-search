from __future__ import annotations
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(os.getenv('CATALOG_DB', ROOT/'db'/'catalog.sqlite3'))
MODEL=DB.with_name('embedding_model.joblib')

def run(*args:str):
    print('+', ' '.join(args), flush=True)
    subprocess.check_call(args, cwd=ROOT)

def healthy() -> bool:
    if not DB.exists() or not MODEL.exists():
        return False
    try:
        con=sqlite3.connect(DB)
        records=int(con.execute('select count(*) from content').fetchone()[0])
        vectors=int(con.execute('select count(*) from content_vectors').fetchone()[0])
        intelligence=int(con.execute('select count(*) from content_intelligence').fetchone()[0])
        platform_rows=int(con.execute('select count(*) from platform_availability').fetchone()[0])
        real_posters=int(con.execute("select count(*) from content where poster_url like 'https://%' or poster_url like 'http://%'").fetchone()[0])
        generated=int(con.execute("select count(*) from content where poster_url like 'data:image/%'").fetchone()[0])
        con.close()
        return records>=1000 and vectors==records and intelligence==records and platform_rows>=0 and real_posters==records and generated==0
    except Exception:
        return False

def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    if healthy():
        print(f'catalog ready: {DB}', flush=True)
        return

    # Vercel deploys must stay deterministic and fast. Building a 1000+ title catalog,
    # crawling poster sources, and fitting embeddings during the Vercel build is too fragile.
    # GitHub Actions publishes an audited db/catalog.sqlite3 + embedding_model.joblib bundle.
    if os.getenv('VERCEL'):
        raise SystemExit(
            "Bundled catalog runtime is missing or failed quality checks. "
            "Wait for the GitHub 'Refresh canonical catalog' workflow to publish "
            "db/catalog.sqlite3 and db/embedding_model.joblib, then redeploy."
        )

    run(sys.executable,'data_pipeline/catalog_builder.py','--db',str(DB),
        '--tvmaze-target',os.getenv('TVMAZE_TARGET','3000'),
        '--china-series-target',os.getenv('CHINA_SERIES_TARGET','220'),
        '--movies-per-country',os.getenv('MOVIES_PER_COUNTRY','70'),
        '--min-records',os.getenv('MIN_RECORDS','1000'),
        '--min-china-series',os.getenv('MIN_CHINA_SERIES','120'))
    poster_cmd=[sys.executable,'scripts/backfill_real_posters.py','--db',str(DB),'--strict']
    if os.getenv('DROP_UNRESOLVED_POSTERS','').lower() in {'1','true','yes'}:
        poster_cmd.append('--drop-unresolved')
    run(*poster_cmd)
    run(sys.executable,'scripts/migrate_content_intelligence.py','--db',str(DB))
    run(sys.executable,'scripts/migrate_platform_availability.py','--db',str(DB))
    run(sys.executable,'scripts/migrate_evidence_corpus.py','--db',str(DB))
    run(sys.executable,'scripts/build_embeddings.py','--db',str(DB),'--model',str(MODEL),'--dim',os.getenv('EMBEDDING_DIM','128'))
    run(sys.executable,'scripts/verify_catalog.py','--db',str(DB),
        '--min-records',os.getenv('MIN_RECORDS','1000'),
        '--min-china-series',os.getenv('MIN_CHINA_SERIES','120'))

if __name__=='__main__':
    main()
