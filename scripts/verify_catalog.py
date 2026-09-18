from __future__ import annotations
import argparse,sqlite3

p=argparse.ArgumentParser()
p.add_argument('--db',default='db/catalog.sqlite3')
p.add_argument('--min-records',type=int,default=1000)
p.add_argument('--min-china-series',type=int,default=150)
a=p.parse_args()

con=None
try:
    con=sqlite3.connect(a.db)
    version=con.execute("SELECT value FROM catalog_meta WHERE key='schema_version'").fetchone()
    records=con.execute('SELECT COUNT(*) FROM content').fetchone()[0]
    vectors=con.execute('SELECT COUNT(*) FROM content_vectors').fetchone()[0]
    intelligence=con.execute('SELECT COUNT(*) FROM content_intelligence').fetchone()[0]
    posters=con.execute("""
        SELECT COUNT(*) FROM content
        WHERE poster_url IS NOT NULL
          AND TRIM(poster_url)<>''
          AND (poster_url LIKE 'https://%' OR poster_url LIKE 'http://%')
    """).fetchone()[0]
    generated=con.execute("""
        SELECT COUNT(*) FROM content
        WHERE poster_url LIKE 'data:image/%' OR poster_url LIKE '%GENERATED POSTER%'
    """).fetchone()[0]
    china_series=con.execute("""
        SELECT COUNT(*) FROM content
        WHERE content_type='series'
          AND (countries_json LIKE '%中国大陆%' OR language IN ('中文','Chinese','Mandarin','Cantonese'))
    """).fetchone()[0]
    model=con.execute("SELECT value FROM catalog_meta WHERE key='embedding_type'").fetchone()
except Exception as exc:
    raise SystemExit(f'catalog validation failed: {exc}')
finally:
    if con:
        try:con.close()
        except Exception:pass

if (
    not version or version[0]!='2.1'
    or records<a.min_records
    or china_series<a.min_china_series
    or vectors!=records
    or intelligence!=records
    or posters!=records
    or generated!=0
    or not model
):
    raise SystemExit(
        f'catalog rejected: schema={version[0] if version else None}, records={records}, '
        f'chinese_series={china_series}, vectors={vectors}, intelligence={intelligence}, '
        f'real_posters={posters}/{records}, generated_posters={generated}, embedding={model}'
    )

print(
    f'catalog ok: schema=2.1 records={records} chinese_series={china_series} '
    f'vectors={vectors} intelligence={intelligence} real_posters={posters}/{records} '
    f'generated_posters=0 embedding={model[0]}'
)
