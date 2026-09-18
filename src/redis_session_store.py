from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from .models import SceneProfile, MemoryItem

class RedisSessionStore:
    def __init__(self,url:str,ttl_seconds:int=60*60*24*7):
        import redis
        self.client=redis.from_url(url,decode_responses=True); self.ttl_seconds=ttl_seconds; self.prefix=os.getenv('REDIS_PREFIX','scene_search')
    def _session_key(self,sid:str)->str: return f'{self.prefix}:session:{sid}'
    def _memory_key(self,user_id:str)->str: return f'{self.prefix}:memories:{user_id}'
    def create(self)->str:
        sid=str(uuid.uuid4()); payload={'profile':SceneProfile().to_dict(),'exposed':[],'turn':0,'updated_at':datetime.now(timezone.utc).isoformat()}
        self.client.set(self._session_key(sid),json.dumps(payload,ensure_ascii=False),ex=self.ttl_seconds); return sid
    def get(self,sid:str):
        raw=self.client.get(self._session_key(sid))
        if not raw:return None
        d=json.loads(raw); self.client.expire(self._session_key(sid),self.ttl_seconds)
        return SceneProfile(**d['profile']),d.get('exposed',[]),int(d.get('turn',0))
    def save(self,sid:str,p:SceneProfile,exposed:list[str],turn:int):
        payload={'profile':p.to_dict(),'exposed':exposed,'turn':turn,'updated_at':datetime.now(timezone.utc).isoformat()}
        self.client.set(self._session_key(sid),json.dumps(payload,ensure_ascii=False),ex=self.ttl_seconds)
    def add_memory(self,user_id:str,item:MemoryItem):
        value={'memory_id':item.memory_id,'text':item.text,'memory_type':item.memory_type,'created_at':item.created_at,'evidence_strength':item.evidence_strength,'source':item.source,'structured':item.structured}
        self.client.hset(self._memory_key(user_id),item.memory_id,json.dumps(value,ensure_ascii=False)); self.client.expire(self._memory_key(user_id),self.ttl_seconds)
    def list_memories(self,user_id:str)->list[MemoryItem]:
        out=[]
        for raw in self.client.hvals(self._memory_key(user_id)):
            d=json.loads(raw); out.append(MemoryItem(**d))
        return out
