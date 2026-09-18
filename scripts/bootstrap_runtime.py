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
        con.close()
        return records>=1000 and vectors==records and intelligence==records
    except Exception:
        return False

def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    if healthy():
        print(f'catalog ready: {DB}', flush=True)
        return
    run(sys.executable,'data_pipeline/catalog_builder.py','--db',str(DB),
        '--tvmaze-target',os.getenv('TVMAZE_TARGET','3000'),
        '--china-series-target',os.getenv('CHINA_SERIES_TARGET','220'),
        '--movies-per-country',os.getenv('MOVIES_PER_COUNTRY','70'),
        '--min-records',os.getenv('MIN_RECORDS','1000'),
        '--min-china-series',os.getenv('MIN_CHINA_SERIES','120'))
    run(sys.executable,'scripts/migrate_content_intelligence.py','--db',str(DB))
    run(sys.executable,'scripts/migrate_evidence_corpus.py','--db',str(DB))
    run(sys.executable,'scripts/build_embeddings.py','--db',str(DB),'--model',str(MODEL),'--dim',os.getenv('EMBEDDING_DIM','128'))
    run(sys.executable,'scripts/verify_catalog.py','--db',str(DB),
        '--min-records',os.getenv('MIN_RECORDS','1000'),
        '--min-china-series',os.getenv('MIN_CHINA_SERIES','120'))

if __name__=='__main__':
    main()
