from __future__ import annotations

"""Backfill and verify REAL poster artwork in the canonical YING catalog.

Poster acceptance policy:
1. A poster must be an HTTP(S) image that can actually be fetched.
2. TVMaze primary images are trusted poster-format assets for TV/series records.
3. TMDB poster_path is preferred for missing/broken poster artwork (requires TMDB_API_TOKEN).
4. Curated poster URLs are accepted only after network verification.
5. Generic Wikidata P18 is not considered poster-specific provenance by itself.

The script never writes generated SVG placeholders. In strict mode every row must end with a
reachable image, otherwise the catalog build fails.
"""

import argparse
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

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


def reachable_image(client: httpx.Client, url: str) -> bool:
    if not valid_real_url(url):
        return False
    try:
        with client.stream(
            "GET",
            url,
            headers={"Range":"bytes=0-2047","Accept":"image/avif,image/webp,image/apng,image/*,*/*;q=0.8"},
        ) as r:
            if r.status_code not in {200,206}:
                return False
            ctype=(r.headers.get("content-type") or "").lower()
            if ctype.startswith("image/"):
                return True
            # Some CDNs omit/lie about content-type. Read only the first small chunk and inspect magic bytes.
            first=b""
            for chunk in r.iter_bytes():
                first+=chunk
                if len(first)>=32:
                    break
            return (
                first.startswith(b"\xff\xd8\xff") or
                first.startswith(b"\x89PNG\r\n\x1a\n") or
                first.startswith(b"RIFF") or
                first.startswith(b"GIF8") or
                first.startswith(b"BM")
            )
    except Exception:
        return False


def pick_year_match(results, year):
    if not results:
        return None
    if not year:
        return results[0]
    def score(r):
        date=r.get("release_date") or r.get("first_air_date") or ""
        ry=int(date[:4]) if len(date)>=4 and date[:4].isdigit() else None
        exact=0 if ry==year else 1 if ry and abs(ry-year)<=1 else 2
        return (exact, -(r.get("popularity") or 0))
    return sorted(results,key=score)[0]


def tvmaze_poster(client: httpx.Client, title: str):
    r=client.get("https://api.tvmaze.com/singlesearch/shows",params={"q":title})
    if r.status_code==404:
        return None
    r.raise_for_status()
    data=r.json()
    image=data.get("image") or {}
    url=image.get("original") or image.get("medium")
    if not valid_real_url(url) or not reachable_image(client,url):
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
    url="https://image.tmdb.org/t/p/w500"+best["poster_path"]
    if not reachable_image(client,url):
        return None
    return {
        "url":url,
        "provider":"tmdb",
        "provider_id":str(best.get("id") or ""),
        "source_url":f"https://www.themoviedb.org/{'movie' if kind=='movie' else 'tv'}/{best.get('id')}",
        "confidence":.95 if year else .88,
    }


def resolve_one(row: dict, token: str, timeout: float):
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent":"YING/1.4 poster-auditor"},
    ) as client:
        existing=row.get("poster_url") or ""
        source=(row.get("source") or "").lower()

        trusted_provenance=(
            source=="tvmaze"
            or source.endswith("_curated")
            or source.startswith("manual_")
        )
        if trusted_provenance and reachable_image(client,existing):
            return {
                "status":"kept",
                "content_id":row["content_id"],
                "url":existing,
                "provider":source or "source",
                "provider_id":row.get("source_id") or "",
                "source_url":row.get("source_url") or "",
                "confidence":.95,
            }

        # Prefer TMDB for poster-specific artwork.
        try:
            found=tmdb_poster(client,token,row["title"],row["content_type"],row.get("release_year"))
        except Exception:
            found=None

        # Keyless fallback for series/animation/variety.
        if found is None and row["content_type"] in {"series","animation","variety"}:
            try:
                found=tvmaze_poster(client,row["title"])
            except Exception:
                found=None

        if found:
            return {"status":"repaired","content_id":row["content_id"],**found}

        return {
            "status":"missing",
            "content_id":row["content_id"],
            "title":row["title"],
            "type":row["content_type"],
            "year":row.get("release_year"),
            "previous_url":existing,
        }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",default="db/catalog.sqlite3")
    ap.add_argument("--strict",action="store_true")
    ap.add_argument("--workers",type=int,default=int(os.getenv("POSTER_WORKERS","10")))
    ap.add_argument("--timeout",type=float,default=float(os.getenv("POSTER_HTTP_TIMEOUT","12")))
    args=ap.parse_args()

    token=os.getenv("TMDB_API_TOKEN","").strip()
    con=sqlite3.connect(args.db)
    con.row_factory=sqlite3.Row
    con.executescript(DDL)
    rows=[dict(r) for r in con.execute("""
      SELECT content_id,title,content_type,release_year,poster_url,source,source_id,source_url
      FROM content ORDER BY content_id
    """).fetchall()]

    now=datetime.now(timezone.utc).isoformat()
    results=[]
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:
        futures=[pool.submit(resolve_one,row,token,args.timeout) for row in rows]
        for idx,future in enumerate(as_completed(futures),start=1):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"status":"error","error":str(exc)[:250]})
            if idx%250==0:
                print(f"poster audit: {idx}/{len(rows)}",flush=True)

    missing=[]
    kept=repaired=0
    for result in results:
        status=result.get("status")
        if status in {"kept","repaired"}:
            if status=="kept": kept+=1
            else: repaired+=1
            con.execute("UPDATE content SET poster_url=? WHERE content_id=?",(result["url"],result["content_id"]))
            con.execute(
                "INSERT OR REPLACE INTO poster_assets VALUES (?,?,?,?,?,?,?)",
                (
                    result["content_id"],result["url"],result["provider"],result.get("provider_id") or "",
                    result.get("source_url") or "",float(result["confidence"]),now,
                )
            )
        elif status=="missing":
            missing.append(result)

    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",("poster_backfill_version","1.4"))
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",("real_poster_count",str(kept+repaired)))
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",("real_poster_missing",str(len(missing))))
    con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",("poster_verified_at",now))
    con.commit()

    total=len(rows)
    report={
        "records":total,
        "existing_verified":kept,
        "repaired":repaired,
        "reachable_real_poster_coverage":round((kept+repaired)/max(1,total),4),
        "unresolved":len(missing),
        "tmdb_configured":bool(token),
        "workers":args.workers,
        "poster_policy":"reachable TVMaze/TMDB/curated poster assets only; generated SVG and generic Wikidata P18 are rejected",
        "missing_sample":missing[:25],
    }
    print(json.dumps(report,ensure_ascii=False,indent=2))
    con.close()

    if args.strict and missing:
        raise SystemExit(
            f"real poster quality gate failed: {len(missing)} titles unresolved. "
            "Configure TMDB_API_TOKEN and rerun; generated placeholders are not accepted."
        )


if __name__=="__main__":
    main()
