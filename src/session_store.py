from __future__ import annotations
import json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from .models import SceneProfile, MemoryItem

class SessionStore:
    def __init__(self,path:str):
        self.path=path; Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.con=sqlite3.connect(path,check_same_thread=False)
        self.con.execute('CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY, profile_json TEXT NOT NULL, exposed_json TEXT NOT NULL, turn INTEGER NOT NULL, updated_at TEXT NOT NULL)')
        self.con.execute('CREATE TABLE IF NOT EXISTS memories(memory_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,text TEXT NOT NULL,memory_type TEXT NOT NULL,created_at TEXT NOT NULL,evidence_strength REAL NOT NULL,source TEXT NOT NULL,structured_json TEXT NOT NULL)')
        self.con.commit()
    def create(self)->str:
        sid=str(uuid.uuid4()); self.con.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(sid,json.dumps(SceneProfile().to_dict(),ensure_ascii=False),'[]',0,datetime.now(timezone.utc).isoformat())); self.con.commit(); return sid
    def get(self,sid:str):
        row=self.con.execute('SELECT profile_json,exposed_json,turn FROM sessions WHERE session_id=?',(sid,)).fetchone()
        if not row: return None
        p=SceneProfile(**json.loads(row[0])); return p,json.loads(row[1]),row[2]
    def save(self,sid:str,p:SceneProfile,exposed:list[str],turn:int):
        self.con.execute('UPDATE sessions SET profile_json=?,exposed_json=?,turn=?,updated_at=? WHERE session_id=?',(json.dumps(p.to_dict(),ensure_ascii=False),json.dumps(exposed),turn,datetime.now(timezone.utc).isoformat(),sid)); self.con.commit()
    def add_memory(self,user_id:str,item:MemoryItem):
        self.con.execute('INSERT OR REPLACE INTO memories VALUES(?,?,?,?,?,?,?,?)',(item.memory_id,user_id,item.text,item.memory_type,item.created_at,item.evidence_strength,item.source,json.dumps(item.structured,ensure_ascii=False))); self.con.commit()
    def list_memories(self,user_id:str)->list[MemoryItem]:
        rows=self.con.execute('SELECT memory_id,text,memory_type,created_at,evidence_strength,source,structured_json FROM memories WHERE user_id=?',(user_id,)).fetchall()
        return [MemoryItem(r[0],r[1],r[2],r[3],r[4],r[5],json.loads(r[6])) for r in rows]
