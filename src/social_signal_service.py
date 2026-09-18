from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx


SOCIAL_SCHEMA_VERSION = "1.0"
DDL = """
CREATE TABLE IF NOT EXISTS social_signals(
    signal_id TEXT PRIMARY KEY,
    content_id TEXT NOT NULL,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_title TEXT,
    snippet TEXT,
    author_id TEXT,
    published_at TEXT,
    engagement REAL NOT NULL DEFAULT 0,
    source_reliability REAL NOT NULL DEFAULT 0,
    authenticity_score REAL NOT NULL DEFAULT 0,
    entity_confidence REAL NOT NULL DEFAULT 0,
    recommendation_signal REAL NOT NULL DEFAULT 0,
    fetched_at TEXT NOT NULL,
    raw_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_social_content ON social_signals(content_id);
CREATE INDEX IF NOT EXISTS idx_social_platform ON social_signals(platform, fetched_at);
"""


@dataclass
class SocialEvidence:
    platform: str
    source_url: str
    source_title: str = ""
    snippet: str = ""
    author_id: str = ""
    published_at: str = ""
    engagement: float = 0.0
    source_reliability: float = 0.0
    authenticity_score: float = 0.0
    entity_confidence: float = 0.0
    recommendation_signal: float = 0.0
    raw: dict[str, Any] | None = None


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().casefold()


def _sig_id(content_id: str, platform: str, url: str, snippet: str) -> str:
    raw=f"{content_id}|{platform}|{url}|{_norm(snippet)[:160]}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _platform_from_url(url: str) -> str:
    host=(urlparse(url).netloc or "").casefold()
    if "xiaohongshu.com" in host or "xhslink.com" in host: return "xiaohongshu"
    if "mp.weixin.qq.com" in host: return "wechat_official"
    if host.endswith("x.com") or host.endswith("twitter.com"): return "x"
    if "douban.com" in host: return "douban"
    if "zhihu.com" in host: return "zhihu"
    if "baidu.com" in host: return "baidu"
    return "web"


def _base_reliability(platform: str, url: str) -> float:
    host=(urlparse(url).netloc or "").casefold()
    if any(x in host for x in ["gov.cn","chinafilm.gov.cn"]): return .98
    if platform=="wechat_official": return .74
    if platform=="xiaohongshu": return .58
    if platform=="x": return .55
    if platform=="douban": return .66
    if platform=="zhihu": return .61
    if platform=="baidu": return .68
    return .52


def _entity_confidence(title: str, text: str) -> float:
    t=_norm(title); body=_norm(text)
    if not t: return 0.0
    if t in body: return .96
    compact=re.sub(r"[^\w\u4e00-\u9fff]+","",t)
    body_compact=re.sub(r"[^\w\u4e00-\u9fff]+","",body)
    return .78 if compact and compact in body_compact else .42


def _recommendation_signal(text: str) -> float:
    body=_norm(text)
    pos=["推荐","值得看","好看","惊喜","上头","喜欢","治愈","好笑","精彩","recommend","worth watching","loved"]
    neg=["不推荐","难看","烂","踩雷","失望","弃剧","boring","disappoint"]
    p=sum(1 for x in pos if x in body); n=sum(1 for x in neg if x in body)
    if p==n==0: return .5
    return max(0.0,min(1.0,.5+.16*(p-n)))


def _authenticity(platform: str, reliability: float, engagement: float, duplicate_penalty: float=0.0) -> float:
    engagement_term=min(.18, math.log1p(max(0.0,engagement))/70.0)
    return max(0.0,min(1.0,reliability+.08+engagement_term-duplicate_penalty))


class SocialSignalService:
    """Social proof is weak evidence, never a hard fact source.

    Direct anti-bot bypassing is intentionally excluded. X uses the official Recent Search API.
    Chinese social/WeChat discovery goes through Baidu AI Search's public web index with site filters.
    """

    def __init__(self, con: sqlite3.Connection):
        self.con=con
        self.con.executescript(DDL)
        self.baidu_key=os.getenv("BAIDU_SEARCH_API_KEY","").strip()
        self.x_token=os.getenv("X_BEARER_TOKEN","").strip()
        self.timeout=float(os.getenv("SOCIAL_SEARCH_TIMEOUT","10"))

    def configured(self) -> dict[str,bool]:
        return {"baidu_ai_search":bool(self.baidu_key),"x_recent_search":bool(self.x_token)}

    def _save(self, content_id: str, title: str, ev: SocialEvidence) -> None:
        now=datetime.now(timezone.utc).isoformat()
        self.con.execute("""
          INSERT OR REPLACE INTO social_signals
          (signal_id,content_id,title,platform,source_url,source_title,snippet,author_id,published_at,
           engagement,source_reliability,authenticity_score,entity_confidence,recommendation_signal,
           fetched_at,raw_json)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,(
            _sig_id(content_id,ev.platform,ev.source_url,ev.snippet),content_id,title,ev.platform,ev.source_url,
            ev.source_title,ev.snippet,ev.author_id,ev.published_at,ev.engagement,ev.source_reliability,
            ev.authenticity_score,ev.entity_confidence,ev.recommendation_signal,now,
            json.dumps(ev.raw or {},ensure_ascii=False)
        ))

    def _baidu_search(self, title: str, sites: list[str] | None=None, top_k: int=12) -> list[SocialEvidence]:
        if not self.baidu_key: return []
        body={
            "messages":[{"content":f'"{title}" 电影 剧集 推荐 影评 观后感',"role":"user"}],
            "search_source":"baidu_search_v2",
            "resource_type_filter":[{"type":"web","top_k":min(50,max(1,top_k))}],
            "search_recency_filter":"year",
        }
        if sites:
            body["search_filter"]={"match":{"site":sites[:20]}}
        headers={"X-Appbuilder-Authorization":f"Bearer {self.baidu_key}","Content-Type":"application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            r=client.post("https://qianfan.baidubce.com/v2/ai_search/web_search",headers=headers,json=body)
            r.raise_for_status(); data=r.json()
        out=[]
        for ref in data.get("references",[]) or []:
            url=ref.get("url") or ""
            text=" ".join([ref.get("title") or "",ref.get("content") or ""])
            platform=_platform_from_url(url)
            rel=_base_reliability(platform,url)
            ent=_entity_confidence(title,text)
            rec=_recommendation_signal(text)
            out.append(SocialEvidence(
                platform=platform,source_url=url,source_title=ref.get("title") or "",
                snippet=(ref.get("content") or "")[:600],published_at=ref.get("date") or "",
                source_reliability=rel,authenticity_score=_authenticity(platform,rel,0),
                entity_confidence=ent,recommendation_signal=rec,raw=ref
            ))
        return out

    def _x_search(self, title: str, max_results: int=20) -> list[SocialEvidence]:
        if not self.x_token: return []
        params={
            "query":f'"{title}" -is:retweet',
            "max_results":max(10,min(100,max_results)),
            "tweet.fields":"created_at,public_metrics,author_id,lang",
        }
        headers={"Authorization":f"Bearer {self.x_token}"}
        with httpx.Client(timeout=self.timeout) as client:
            r=client.get("https://api.x.com/2/tweets/search/recent",headers=headers,params=params)
            r.raise_for_status(); data=r.json()
        out=[]
        for post in data.get("data",[]) or []:
            metrics=post.get("public_metrics") or {}
            engagement=sum(float(metrics.get(k,0) or 0) for k in ["like_count","reply_count","retweet_count","quote_count"])
            text=post.get("text") or ""
            url=f"https://x.com/i/web/status/{post.get('id')}"
            rel=_base_reliability("x",url)
            out.append(SocialEvidence(
                platform="x",source_url=url,source_title="X public post",snippet=text[:600],
                author_id=post.get("author_id") or "",published_at=post.get("created_at") or "",
                engagement=engagement,source_reliability=rel,
                authenticity_score=_authenticity("x",rel,engagement),
                entity_confidence=_entity_confidence(title,text),
                recommendation_signal=_recommendation_signal(text),raw=post
            ))
        return out

    def refresh(self, content_id: str, title: str) -> dict[str,Any]:
        evidence=[]
        # No direct Xiaohongshu crawler: official open platform is commerce-focused, not general note search.
        # Search indexed public pages instead.
        try:
            evidence += self._baidu_search(title,[
                "www.xiaohongshu.com","mp.weixin.qq.com","movie.douban.com","www.zhihu.com"
            ],top_k=20)
        except Exception as exc:
            evidence.append(SocialEvidence(platform="baidu_error",source_url="",snippet=str(exc)[:220]))
        try:
            evidence += self._x_search(title,20)
        except Exception as exc:
            evidence.append(SocialEvidence(platform="x_error",source_url="",snippet=str(exc)[:220]))

        # Duplicate text is a low-quality authenticity signal; keep one canonical item per fingerprint.
        seen={}
        cleaned=[]
        for ev in evidence:
            if not ev.source_url: continue
            fp=hashlib.sha1(_norm(ev.snippet)[:180].encode("utf-8")).hexdigest()
            if fp in seen: continue
            seen[fp]=1
            cleaned.append(ev)
            self._save(content_id,title,ev)
        self.con.commit()
        return self.context(content_id)

    def aggregate(self, content_id: str) -> dict[str,Any]:
        rows=self.con.execute("""
          SELECT * FROM social_signals WHERE content_id=?
          ORDER BY fetched_at DESC LIMIT 80
        """,(content_id,)).fetchall()
        if not rows:
            return {"score":0.0,"confidence":0.0,"count":0,"platforms":[]}
        useful=[r for r in rows if r["entity_confidence"]>=.65 and r["authenticity_score"]>=.45]
        if not useful:
            return {"score":0.0,"confidence":0.0,"count":len(rows),"platforms":[]}
        weights=[]; values=[]
        for r in useful:
            w=float(r["authenticity_score"])*float(r["entity_confidence"])
            weights.append(w);values.append(float(r["recommendation_signal"]))
        score=sum(v*w for v,w in zip(values,weights))/max(1e-9,sum(weights))
        platforms=sorted({r["platform"] for r in useful})
        cross=min(1.0,len(platforms)/3.0)
        confidence=min(1.0,.35+.08*len(useful)+.22*cross)
        return {"score":round(score,4),"confidence":round(confidence,4),"count":len(useful),"platforms":platforms}

    def context(self, content_id: str, limit: int=10) -> dict[str,Any]:
        rows=self.con.execute("""
          SELECT platform,source_url,source_title,snippet,author_id,published_at,engagement,
                 source_reliability,authenticity_score,entity_confidence,recommendation_signal,fetched_at
          FROM social_signals WHERE content_id=?
          ORDER BY authenticity_score*entity_confidence DESC, fetched_at DESC LIMIT ?
        """,(content_id,limit)).fetchall()
        return {
            "aggregate":self.aggregate(content_id),
            "configured":self.configured(),
            "evidence":[dict(r) for r in rows],
            "policy":{
                "social_weight":"weak ranking signal only",
                "hard_constraints":"never overridden",
                "truth_checks":["entity match","source reliability","dedupe","cross-platform confirmation","time freshness"],
                "xiaohongshu":"no direct anti-bot crawler; use indexed public pages / authorized sources",
            }
        }
