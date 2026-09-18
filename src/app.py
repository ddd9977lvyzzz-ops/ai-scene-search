from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .retriever import CatalogRetriever
from .session_store import SessionStore
from .redis_session_store import RedisSessionStore
from .agent import SceneSearchAgent
from .memory import retrieve_memories
from .catalog_service import CatalogService
from .event_store import EventStore
from .features import public_feature_schema

BASE_DIR = Path(__file__).resolve().parents[1]
CATALOG_DB = os.getenv('CATALOG_DB', str(BASE_DIR / 'db' / 'catalog.sqlite3'))
SESSION_DB = os.getenv('SESSION_DB', str(BASE_DIR / 'db' / 'session.sqlite3'))
EVENT_DB = os.getenv('EVENT_DB', str(BASE_DIR / 'db' / 'events.sqlite3'))
WEB_DIR = BASE_DIR / 'web'

if os.getenv('SESSION_BACKEND','sqlite').lower() == 'redis' and os.getenv('REDIS_URL'):
    store = RedisSessionStore(os.environ['REDIS_URL'], int(os.getenv('SESSION_TTL_SECONDS','604800')))
else:
    store = SessionStore(SESSION_DB)
events = EventStore(EVENT_DB)
catalog = CatalogService(CATALOG_DB)
agent = SceneSearchAgent(CatalogRetriever(CATALOG_DB), store, events)

app = FastAPI(title='AI Scene Search Web Demo', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'], allow_credentials=False, allow_methods=['*'], allow_headers=['*']
)


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class MemoryQuery(BaseModel):
    user_id: str
    query: str
    k: int = 5


class FeedbackIn(BaseModel):
    event_name: str
    content_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@app.get('/health')
def health():
    return {'ok': True, 'version': '1.0.0', 'catalog_count': catalog.count(), 'catalog_db': str(Path(CATALOG_DB).resolve()), 'catalog_quality': catalog.quality_stats()}


@app.get('/v1/demo/meta')
def demo_meta():
    quality = catalog.quality_stats()
    return {
        'catalog_count': catalog.count(),
        'content_types': catalog.content_types(),
        'quality': quality,
        'data_note': ('%s 部内容 · %s 部国产剧 · 海报 %.1f%% · %s 维向量 %s/%s · Evidence %s 条' % (quality['records'], quality['china_series'], quality['poster_coverage']*100, quality.get('embedding_dim',0), quality['vectors'], quality['records'], quality.get('evidence_chunks',0))),
        'retrieval_note': '精确约束 → 混合召回 → 硬过滤 → 场景重排 → 证据化解释；探索模式只改变排序，不越过硬条件。',
        'starter_prompts': [
            '我想看小众恋爱片',
            '最近想自己追一部国产剧，节奏快一点，不要太虐',
            '周末自己看，想刺激一点，不要恐怖，两小时内',
            '和朋友聚会，想看轻松好笑的电影',
            '跟家人饭后看，轻松一点，不要恐怖',
            '一个人睡前看，想治愈一点，90分钟内',
        ],
    }


@app.get('/v1/demo/feature-schema')
def feature_schema():
    return public_feature_schema()


@app.post('/v1/sessions')
def new_session():
    session_id = store.create()
    events.log('session_created', session_id)
    return {'session_id': session_id}


@app.get('/v1/sessions/{session_id}')
def get_session(session_id: str):
    state = store.get(session_id)
    if state is None:
        raise HTTPException(404, 'session_not_found')
    profile, exposed, turn = state
    return {'session_id': session_id, 'turn': turn, 'profile': profile.to_dict(), 'exposed_ids': exposed}


@app.post('/v1/sessions/{session_id}/chat')
def chat(session_id: str, body: ChatIn):
    events.log('user_message', session_id, payload={'text': body.text})
    try:
        return agent.chat(session_id, body.text)
    except KeyError:
        raise HTTPException(404, 'session_not_found')


@app.post('/v1/sessions/{session_id}/feedback')
def feedback(session_id: str, body: FeedbackIn):
    if store.get(session_id) is None:
        raise HTTPException(404, 'session_not_found')
    events.log(body.event_name, session_id, body.content_id, body.payload)
    return {'ok': True}


@app.get('/v1/catalog/browse')
def browse(content_type: str | None = None, limit: int = Query(18, ge=1, le=60), offset: int = Query(0, ge=0)):
    return {'results': catalog.browse(content_type=content_type, limit=limit, offset=offset)}


@app.get('/v1/catalog/search')
def catalog_search(q: str, limit: int = Query(20, ge=1, le=40)):
    return {'results': catalog.search(q, limit=limit)}


@app.get('/v1/content/{content_id:path}')
def content_detail(content_id: str):
    item = catalog.get(content_id)
    if not item:
        raise HTTPException(404, 'content_not_found')
    return item


@app.post('/v1/memory/retrieve')
def memory_retrieve(body: MemoryQuery):
    memories = store.list_memories(body.user_id)
    ranked = retrieve_memories(body.query, memories, body.k)
    return {'results': [
        {'memory_id': m.memory_id, 'text': m.text, 'memory_type': m.memory_type, 'score_breakdown': s}
        for _, m, s in ranked
    ]}


app.mount('/', StaticFiles(directory=str(WEB_DIR), html=True), name='web')
