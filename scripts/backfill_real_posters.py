from __future__ import annotations

"""Backfill REAL poster artwork into the canonical catalog.

Priority:
1) existing HTTP poster
2) TVMaze show images (free public API, series)
3) TMDB search + poster_path (movies/TV; requires TMDB_API_TOKEN)

The script never writes generated SVG placeholders. In strict mode unresolved titles fail the build.
"""

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from urllib.parse import quote

import httpx


DDL = """
CREATE TABLE IF NOT EXISTS poster_assets(
    content_id TEXT PRIMARY KEY,
    poster_url TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_id TEXT,
    source_url TEXT,
    confidence REAL NOT NULL,
    checked_at TEXT NOT NULL
);
"""


def valid_real_url(url: str | None) -> bool:
    u=(url or "").strip().lower()
    return u.startswith("https://") or u.startswith("http://")


def pick_year_match(results, year):
    if not results:
        return None
    if not year:
        return results[0]
    def score(r):
        date=r.get("release_date") or r.get("first_air_date") or ""
        ry=int(date[:4]) if len(date)>=4 and date[:4].isdigit() else None
        return (0 if ry==year else 1 if ry and abs(ry-year)<=1 else 2, -(r.get("popularity") or 0))
    return sorted(results,key=score)[0]


def tvmaze_poster(client: httpx.Client, title: str):
    r=client.get("https://api.tvmaze.com/singlesearch/shows",params={"q":title})
    if r.status_code==404:
        return None
    r.raise_for_status()
    data=r.json()
    image=data.get("image") or {}
    url=image.get("original") or image.get("medium")
    if not valid_real_url(url):
        return None
    return {
        "url":url,
        "provider":"tvmaze_search",
        "provider_id":str(data.get("id") or ""),
        "source_url":data.get("url") or "",
        "confidence":.88,
    }


def tmdb_poster(client: httpx.Client, token: str, title: str, content_type: str, year: int | None):
    if not token:
        return None
    kind="movie" if content_type=="movie" else "tv"
    params={"query":title,"language":"zh-CN","include_adult":"false"}
    if year:
        params["year" if kind=="movie" else "first_air_date_year"]=str(year)
    r=client.get(
        f"https://api.themoviedb.org/3/search/{kind}",
        params=params,
        headers={"Authorization":f"Bearer {token}","accept":"application/json"},
    )
    r.raise_for_status()
    best=pick_year_match(r.json().get("results") or [],year)
    if not best or not best.get("poster_path"):
        return None
    return {
        "url":"https://image.tmdb.org/t/p/w500"+best["poster_path"],
        "provider":"tmdb",
        "provider_id":str(best.get("id") or ""),
        "source_url":f"https://www.themoviedb.org/{'movie' if kind=='movie' else 'tv'}/{best.get('id')}",
        "confidence":.94 if year else .86,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",default="db/catalog.sqlite3")
    ap.add_argument("--strict",action="store_true")
    ap.add_argument("--sleep",type=float,default=.04)
    args=ap.parse_args()

    token=os.getenv("TMDB_API_TOKEN","").strip()
    con=sqlite3.connect(args.db)
    con.row_factory=sqlite3.Row
    con.executescript(DDL)
    rows=con.execute("""
      SELECT content_id,title,content_type,release_year,poster_url,source,source_id
      FROM content ORDER BY content_id
    """).fetchall()

    now=datetime.now(timezone.utc).isoformat()
    missing=[]
    repaired=0
    kept=0
    with httpx.Client(timeout=15,follow_redirects=True,headers={"User-Agent":"YING/1.3 poster-backfill"}) as client:
        for row in rows:
            existing=row["poster_url"] or ""
            source=(row["source"] or "").lower()
            # TVMaze primary show images are documented as poster-format images. Curated records
            # are manually sourced poster assets. Generic Wikidata P18 is NOT automatically treated
            # as a poster because it can be a still, logo, or other image.
            trusted_existing = valid_real_url(existing) and (
                source=="tvmaze" or source.endswith("_curated") or source.startswith("manual_")
            )
            if trusted_existing:
                kept+=1
                con.execute(
                    "INSERT OR REPLACE INTO poster_assets VALUES (?,?,?,?,?,?,?)",
                    (row["content_id"],existing,source or "source","",row["source_id"] or "",.94,now)
                )
                continue

            found=None
            # TMDB is the preferred backfill because poster_path is explicitly poster artwork.
            try:
                found=tmdb_poster(client,token,row["title"],row["content_type"],row["release_year"])
            except Exception:
                found=None

            # If TMDB is unavailable or has no match, TVMaze is a keyless fallback for series.
            if found is None and row["content_type"] in {"series","animation","variety"}:
                try:
                    found=tvmaze_poster(client,row["title"])
                except Exception:
                    found=None

            if found:
                con.execute("UPDATE content SET poster_url=? WHERE content_id=?",(found["url"],row["content_id"]))
                con.execute(
                    "INSERT OR REPLACE INTO poster_assets VALUES (?,?,?,?,?,?,?)",
                    (row["content_id"],found["url"],found["provider"],found["provider_id"],found["source_url"],found["confidence"],now)
                )
                repaired+=1
            else:
                missing.append({"content_id":row["content_id"],"title":row["title"],"type":row["content_type"],"year":row["release_year"]})
            time.sleep(args.sleep)

    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",("poster_backfill_version","1.0"))
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",("real_poster_count",str(kept+repaired)))
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",("real_poster_missing",str(len(missing))))
    con.commit()
    total=len(rows)
    print(json.dumps({
        "records":total,
        "existing_real":kept,
        "repaired":repaired,
        "real_poster_coverage":round((kept+repaired)/max(1,total),4),
        "unresolved":len(missing),
        "tmdb_configured":bool(token),
        "poster_policy":"TVMaze/TMDB/curated poster assets only; generic Wikidata P18 is not sufficient",
        "missing_sample":missing[:25],
    },ensure_ascii=False,indent=2))
    con.close()

    if args.strict and missing:
        raise SystemExit(
            f"real poster quality gate failed: {len(missing)} titles unresolved. "
            "Configure TMDB_API_TOKEN and rerun; generated placeholders are not accepted."
        )


if __name__=="__main__":
    main()
