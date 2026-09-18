from __future__ import annotations

"""Public-data catalog builder.

This script intentionally separates source ingestion from content intelligence. It builds the
canonical entity/metadata layer from TVMaze and Wikidata, then the migration scripts enrich the
records with scene/tone/risk/surprise evidence and the embedding script builds a 128d semantic
index.

No anti-bot bypassing is used. Sources are public APIs and requests use a descriptive User-Agent,
bounded concurrency and retries.
"""

import argparse
import html
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "2.1"
USER_AGENT = "ai-scene-search/1.0 (portfolio catalog builder; public API client)"

COUNTRIES = {
    "China": "Q148",
    "Japan": "Q17",
    "South Korea": "Q884",
    "United States": "Q30",
    "United Kingdom": "Q145",
    "France": "Q142",
    "Germany": "Q183",
}

PLATFORM_ALIASES = {
    "Tencent Video": "tencent_video",
    "腾讯视频": "tencent_video",
    "iQIYI": "iqiyi",
    "爱奇艺": "iqiyi",
    "Youku": "youku",
    "优酷": "youku",
    "Mango TV": "mango_tv",
    "芒果TV": "mango_tv",
    "Netflix": "netflix",
    "Disney+": "disney_plus",
    "Hulu": "hulu",
    "Amazon Prime Video": "prime_video",
    "HBO Max": "max",
    "Max": "max",
}

def clean_html(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def year_of(value: str | None) -> int | None:
    if not value:
        return None
    m = re.match(r"(\d{4})", str(value))
    return int(m.group(1)) if m else None

def norm_title(value: str) -> str:
    return re.sub(r"[\W_]+", "", (value or "").casefold())

def generated_poster_url(title: str, year: int | None = None) -> str:
    """Stable SVG data-URI fallback so every catalog row has a renderable poster.

    Source posters are always preferred. This fallback is deliberately marked by its
    data: URI and contains only title/year, so it is safe for a portfolio demo and
    never masquerades as an official key art asset.
    """
    safe_title=html.escape((title or "此刻看什么")[:28])
    safe_year=str(year or "")
    hue=sum(ord(ch) for ch in safe_title)%360
    hue2=(hue+67)%360
    svg=f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="hsl({hue} 35% 18%)"/><stop offset="1" stop-color="hsl({hue2} 48% 44%)"/>
    </linearGradient></defs>
    <rect width="600" height="900" rx="28" fill="url(#g)"/>
    <circle cx="500" cy="160" r="150" fill="white" opacity=".08"/>
    <text x="48" y="630" fill="white" font-family="sans-serif" font-size="28" opacity=".72">SCENE · {safe_year}</text>
    <foreignObject x="48" y="670" width="510" height="160">
      <div xmlns="http://www.w3.org/1999/xhtml" style="font:700 56px/1.15 sans-serif;color:white;word-break:break-all">{safe_title}</div>
    </foreignObject>
    <text x="48" y="852" fill="white" font-family="sans-serif" font-size="18" opacity=".62">AI SCENE SEARCH · GENERATED POSTER</text>
    </svg>"""
    return "data:image/svg+xml;charset=UTF-8,"+urllib.parse.quote(svg, safe="")


def uniq(items):
    return list(dict.fromkeys(x for x in items if x not in (None, "", [])))

def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

def platform_id(name: str | None) -> str | None:
    if not name:
        return None
    for key, value in PLATFORM_ALIASES.items():
        if key.casefold() in name.casefold():
            return value
    return None

class Fetcher:
    def __init__(self, retries: int = 3, sleep: float = .25):
        self.retries = retries
        self.sleep = sleep

    def json(self, url: str, *, timeout: int = 30) -> Any:
        last = None
        for attempt in range(self.retries):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                })
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                last = exc
                time.sleep(self.sleep * (attempt + 1))
        raise RuntimeError(f"fetch failed: {url}: {last}")

    def sparql(self, query: str) -> list[dict[str, Any]]:
        url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({
            "query": query,
            "format": "json",
        })
        data = self.json(url, timeout=60)
        return data.get("results", {}).get("bindings", [])

@dataclass
class Record:
    content_id: str
    title: str
    original_title: str = ""
    aliases: list[str] = field(default_factory=list)
    content_type: str = "series"
    release_year: int | None = None
    runtime_minutes: int | None = None
    episode_runtime_minutes: int | None = None
    countries: list[str] = field(default_factory=list)
    language: str = ""
    genres: list[str] = field(default_factory=list)
    overview: str = ""
    poster_url: str = ""
    backdrop_url: str = ""
    origin_platforms: list[str] = field(default_factory=list)
    cast: list[str] = field(default_factory=list)
    directors: list[str] = field(default_factory=list)
    creators: list[str] = field(default_factory=list)
    source: str = ""
    source_id: str = ""
    source_url: str = ""
    popularity: float | None = None
    rating_score: float | None = None

def infer_features(r: Record) -> dict[str, Any]:
    genres = {x.casefold() for x in r.genres}
    text = f"{r.title} {r.overview}".casefold()
    scene, emotion, watching, audience, pace, risks, rel, themes = [], [], [], [], [], [], [], []

    if "comedy" in genres:
        emotion += ["funny", "light", "relaxing"]
        audience += ["friends"]
        pace += ["lively"]
    if "romance" in genres:
        emotion += ["romantic"]
        rel += ["romantic"]
        themes += ["romance_theme"]
    if genres & {"action", "adventure", "thriller"}:
        emotion += ["exciting", "tense"]
        pace += ["fast"]
    if genres & {"mystery", "crime", "thriller"}:
        emotion += ["thought_provoking"]
        themes += ["mystery_or_crime"]
    if "horror" in genres:
        emotion += ["scary", "tense"]
        risks += ["fear_or_horror"]
    if genres & {"action", "crime", "war"}:
        risks += ["violence_possible"]
    if "family" in genres:
        audience += ["family"]
        rel += ["family"]
    if "animation" in genres:
        audience += ["family"]
    if "documentary" in genres:
        themes += ["nonfiction"]
    if any(x in text for x in ["friend", "friends", "友情", "朋友"]):
        rel += ["friendship"]
    if any(x in text for x in ["family", "mother", "father", "daughter", "son", "家庭", "父亲", "母亲"]):
        rel += ["family"]
    if any(x in text for x in ["school", "college", "teen", "youth", "校园", "青春"]):
        themes += ["coming_of_age"]
    if any(x in text for x in ["workplace", "office", "career", "职场", "公司"]):
        themes += ["workplace"]
    if any(x in text for x in ["death", "grief", "terminal", "funeral", "死亡", "葬礼", "绝症"]):
        risks += ["emotionally_heavy", "death_or_grief"]

    cognitive = "medium"
    if genres & {"mystery", "thriller", "science-fiction", "sci-fi"}:
        cognitive = "high"
    elif genres & {"comedy", "family"}:
        cognitive = "low"

    if r.content_type == "series":
        scene += ["solo"]
        watching += ["bingeable"]
    elif r.content_type == "movie":
        scene += ["solo", "weekend"]
    if "comedy" in genres:
        scene += ["friends", "party"]
        watching += ["background_friendly"]
    if "family" in genres:
        scene += ["family", "meal"]

    overview_signal = 1 if len(r.overview) >= 80 else .5 if r.overview else 0
    genre_signal = 1 if r.genres else 0
    tag_confidence = round(.35 + .25 * overview_signal + .25 * genre_signal + .15 * bool(r.source_url), 3)
    return {
        "scene_tags": uniq(scene),
        "emotion_tags": uniq(emotion),
        "watching_tags": uniq(watching),
        "audience_tags": uniq(audience),
        "pace_tags": uniq(pace or ["moderate"]),
        "risk_tags": uniq(risks),
        "relationship_tags": uniq(rel),
        "theme_tags": uniq(themes),
        "cognitive_load": cognitive,
        "tag_confidence": min(1.0, tag_confidence),
        "tag_provenance": {
            "method": "source_metadata_plus_deterministic_rules",
            "source": r.source,
            "note": "Scene/risk features are conservative metadata-derived signals; specific scene-level triggers require richer evidence.",
        },
    }

def tvmaze_records(fetcher: Fetcher, target: int) -> list[Record]:
    out: list[Record] = []
    page = 0
    while len(out) < target and page < 20:
        try:
            shows = fetcher.json(f"https://api.tvmaze.com/shows?page={page}")
        except RuntimeError:
            break
        if not isinstance(shows, list) or not shows:
            break
        for s in shows:
            genres = s.get("genres") or []
            country = ((s.get("network") or {}).get("country") or {}).get("name")
            if not country:
                country = ((s.get("webChannel") or {}).get("country") or {}).get("name")
            channel = (s.get("webChannel") or {}).get("name") or (s.get("network") or {}).get("name")
            platform = platform_id(channel)
            typ = "series"
            if s.get("type") in {"Reality", "Game Show", "Talk Show", "Variety"}:
                typ = "variety"
            if any(str(g).casefold() == "animation" for g in genres):
                typ = "animation"
            image = s.get("image") or {}
            rating = (s.get("rating") or {}).get("average")
            out.append(Record(
                content_id=f"tvmaze:{s.get('id')}",
                title=s.get("name") or "",
                original_title=s.get("name") or "",
                content_type=typ,
                release_year=year_of(s.get("premiered")),
                episode_runtime_minutes=s.get("averageRuntime") or s.get("runtime"),
                countries=[country] if country else [],
                language=s.get("language") or "",
                genres=genres,
                overview=clean_html(s.get("summary")),
                poster_url=image.get("original") or image.get("medium") or "",
                origin_platforms=[platform] if platform else [],
                source="tvmaze",
                source_id=str(s.get("id")),
                source_url=(s.get("_links") or {}).get("self", {}).get("href") or s.get("url") or "",
                popularity=float(s.get("weight") or 0),
                rating_score=float(rating) if rating is not None else None,
            ))
            if len(out) >= target:
                break
        page += 1
        time.sleep(.08)
    return out

def _wd_value(binding: dict, key: str) -> str:
    return (binding.get(key) or {}).get("value") or ""

def wikidata_records(fetcher: Fetcher, *, kind: str, country_qid: str, limit: int) -> list[Record]:
    instance_qid = "Q11424" if kind == "movie" else "Q5398426"
    # Oversample because OPTIONAL genre rows can duplicate the same work.
    q = f"""
    SELECT ?item ?itemLabel ?itemDescription ?date ?image ?genreLabel WHERE {{
      ?item wdt:P31 wd:{instance_qid};
            wdt:P495 wd:{country_qid}.
      OPTIONAL {{ ?item wdt:P577 ?date. }}
      OPTIONAL {{ ?item wdt:P18 ?image. }}
      OPTIONAL {{ ?item wdt:P136 ?genre. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en".
        ?item rdfs:label ?itemLabel.
        ?item schema:description ?itemDescription.
        ?genre rdfs:label ?genreLabel.
      }}
    }}
    LIMIT {max(limit * 6, 600)}
    """
    try:
        rows = fetcher.sparql(q)
    except RuntimeError:
        return []
    grouped: dict[str, dict[str, Any]] = {}
    for b in rows:
        item = _wd_value(b, "item")
        qid = item.rsplit("/", 1)[-1]
        if not qid:
            continue
        d = grouped.setdefault(qid, {
            "title": _wd_value(b, "itemLabel"),
            "description": _wd_value(b, "itemDescription"),
            "date": _wd_value(b, "date"),
            "image": _wd_value(b, "image"),
            "genres": [],
        })
        g = _wd_value(b, "genreLabel")
        if g and not g.startswith("Q"):
            d["genres"].append(g)
    out=[]
    for qid,d in grouped.items():
        title=d["title"]
        if not title or title.startswith("Q"):
            continue
        genres=uniq(d["genres"])
        out.append(Record(
            content_id=f"wikidata:{qid}",
            title=title,
            original_title=title,
            content_type=kind,
            release_year=year_of(d["date"]),
            countries=["中国大陆"] if country_qid=="Q148" else [],
            language="Chinese" if country_qid=="Q148" else "",
            genres=genres,
            overview=d["description"],
            poster_url=d["image"],
            source="wikidata",
            source_id=qid,
            source_url=f"https://www.wikidata.org/wiki/{qid}",
        ))
        if len(out)>=limit:
            break
    return out

def china_series_records(fetcher: Fetcher, limit: int) -> list[Record]:
    # Direct Wikidata series query provides a China-focused floor independent of TVMaze coverage.
    # Poster resolution happens later; do not discard titles here just because P18 is missing.
    return wikidata_records(fetcher, kind="series", country_qid="Q148", limit=limit)

def merge_records(records: list[Record]) -> list[Record]:
    by_key: dict[tuple, Record] = {}
    by_id: dict[str, Record] = {}
    for r in records:
        if not r.title:
            continue
        if r.content_id in by_id:
            continue
        key=(r.content_type,norm_title(r.title),r.release_year or 0)
        existing=by_key.get(key)
        if existing:
            # Prefer TVMaze's richer overview/poster/runtime but merge useful metadata.
            if len(r.overview)>len(existing.overview):
                existing.overview=r.overview
            if not existing.poster_url and r.poster_url:
                existing.poster_url=r.poster_url
            existing.genres=uniq([*existing.genres,*r.genres])
            existing.countries=uniq([*existing.countries,*r.countries])
            existing.origin_platforms=uniq([*existing.origin_platforms,*r.origin_platforms])
            continue
        by_key[key]=r
        by_id[r.content_id]=r
    return list(by_key.values())

DDL = """
CREATE TABLE IF NOT EXISTS catalog_meta(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS content(
    content_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_title TEXT,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    content_type TEXT NOT NULL,
    release_year INTEGER,
    runtime_minutes INTEGER,
    episode_runtime_minutes INTEGER,
    countries_json TEXT NOT NULL DEFAULT '[]',
    language TEXT,
    genres_json TEXT NOT NULL DEFAULT '[]',
    overview TEXT,
    poster_url TEXT,
    backdrop_url TEXT,
    origin_platforms_json TEXT NOT NULL DEFAULT '[]',
    cast_json TEXT NOT NULL DEFAULT '[]',
    directors_json TEXT NOT NULL DEFAULT '[]',
    creators_json TEXT NOT NULL DEFAULT '[]',
    source TEXT,
    source_id TEXT,
    source_url TEXT,
    search_text TEXT NOT NULL,
    scene_tags_json TEXT NOT NULL DEFAULT '[]',
    emotion_tags_json TEXT NOT NULL DEFAULT '[]',
    watching_tags_json TEXT NOT NULL DEFAULT '[]',
    audience_tags_json TEXT NOT NULL DEFAULT '[]',
    pace_tags_json TEXT NOT NULL DEFAULT '[]',
    risk_tags_json TEXT NOT NULL DEFAULT '[]',
    relationship_tags_json TEXT NOT NULL DEFAULT '[]',
    theme_tags_json TEXT NOT NULL DEFAULT '[]',
    cognitive_load TEXT,
    tag_confidence REAL NOT NULL DEFAULT 0,
    tag_provenance_json TEXT NOT NULL DEFAULT '{}',
    platform_evidence_json TEXT NOT NULL DEFAULT '{}',
    rating_score REAL,
    popularity REAL,
    data_quality_score REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS content_vectors(
    content_id TEXT PRIMARY KEY,
    vector_type TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector_json TEXT NOT NULL,
    source_text TEXT NOT NULL
);
"""

def quality_score(r: Record) -> float:
    score=0
    score += .18 if r.overview else 0
    score += .16 if r.poster_url else 0
    score += .15 if r.genres else 0
    score += .12 if r.release_year else 0
    score += .10 if (r.runtime_minutes or r.episode_runtime_minutes) else 0
    score += .10 if r.countries else 0
    score += .08 if r.language else 0
    score += .06 if r.source_url else 0
    score += .05 if r.origin_platforms else 0
    return round(min(1.0, score), 3)

def search_text(r: Record, f: dict[str, Any]) -> str:
    parts=[
        r.title,r.original_title," ".join(r.aliases),r.overview," ".join(r.genres),
        " ".join(r.countries),r.language," ".join(r.origin_platforms),
        " ".join(f["scene_tags"])," ".join(f["emotion_tags"])," ".join(f["watching_tags"]),
        " ".join(f["audience_tags"])," ".join(f["pace_tags"])," ".join(f["risk_tags"]),
        " ".join(f["relationship_tags"])," ".join(f["theme_tags"]),f["cognitive_load"],
    ]
    return re.sub(r"\s+"," "," ".join(x for x in parts if x)).strip()

def write_db(path: str, records: list[Record]) -> None:
    db=Path(path)
    db.parent.mkdir(parents=True,exist_ok=True)
    if db.exists():
        db.unlink()
    con=sqlite3.connect(db)
    con.executescript(DDL)
    rows=[]
    for r in records:
        f=infer_features(r)
        platform_evidence={p:{"source":r.source,"source_url":r.source_url,"status":"source_metadata"} for p in r.origin_platforms}
        rows.append((
            r.content_id,r.title,r.original_title,json_text(r.aliases),r.content_type,r.release_year,
            r.runtime_minutes,r.episode_runtime_minutes,json_text(r.countries),r.language,json_text(r.genres),
            r.overview,r.poster_url,r.backdrop_url,json_text(r.origin_platforms),json_text(r.cast),
            json_text(r.directors),json_text(r.creators),r.source,r.source_id,r.source_url,
            search_text(r,f),json_text(f["scene_tags"]),json_text(f["emotion_tags"]),json_text(f["watching_tags"]),
            json_text(f["audience_tags"]),json_text(f["pace_tags"]),json_text(f["risk_tags"]),
            json_text(f["relationship_tags"]),json_text(f["theme_tags"]),f["cognitive_load"],
            f["tag_confidence"],json_text(f["tag_provenance"]),json_text(platform_evidence),
            r.rating_score,r.popularity,quality_score(r)
        ))
    con.executemany("""
      INSERT INTO content VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    try:
        con.execute("DROP TABLE IF EXISTS content_fts")
        con.execute("CREATE VIRTUAL TABLE content_fts USING fts5(content_id UNINDEXED, search_text)")
        con.executemany("INSERT INTO content_fts(content_id,search_text) VALUES (?,?)",[(r[0],r[21]) for r in rows])
    except sqlite3.OperationalError:
        pass
    meta={
        "schema_version":SCHEMA_VERSION,
        "poster_policy":"real_source_only_backfill_required",
        "record_count":str(len(records)),
        "builder":"public_api_catalog_builder_v1",
        "sources":"tvmaze,wikidata,curated_2026_official_public_pages",
    }
    for key,value in meta.items():
        con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",(key,value))
    con.commit()
    con.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",default="db/catalog.sqlite3")
    ap.add_argument("--tvmaze-target",type=int,default=3000)
    ap.add_argument("--china-series-target",type=int,default=220)
    ap.add_argument("--movies-per-country",type=int,default=70)
    ap.add_argument("--min-records",type=int,default=1000)
    ap.add_argument("--min-china-series",type=int,default=120)
    args=ap.parse_args()

    fetcher=Fetcher()
    records=tvmaze_records(fetcher,args.tvmaze_target)
    china=china_series_records(fetcher,args.china_series_target)
    records.extend(china)
    from curated_2026 import curated_2026_records
    records.extend(curated_2026_records(Record))
    for _,qid in COUNTRIES.items():
        records.extend(wikidata_records(fetcher,kind="movie",country_qid=qid,limit=args.movies_per_country))
    records=merge_records(records)

    china_series=sum(1 for r in records if r.content_type=="series" and (
        any("中国" in c or c=="China" for c in r.countries) or r.language in {"Chinese","Mandarin","Cantonese","中文"}
    ))
    if len(records)<args.min_records:
        raise SystemExit(f"catalog quality gate failed: only {len(records)} records")
    if china_series<args.min_china_series:
        raise SystemExit(f"catalog quality gate failed: only {china_series} China/Chinese series")

    write_db(args.db,records)
    print(json.dumps({
        "schema_version":SCHEMA_VERSION,
        "records":len(records),
        "china_series":china_series,
        "tvmaze_records":sum(1 for x in records if x.source=="tvmaze"),
        "wikidata_records":sum(1 for x in records if x.source=="wikidata"),
        "db":args.db,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
