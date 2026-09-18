from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class EventStore:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.execute('''CREATE TABLE IF NOT EXISTS event_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            session_id TEXT,
            event_name TEXT NOT NULL,
            content_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}'
        )''')
        self.con.commit()

    def log(self, event_name: str, session_id: str | None = None, content_id: str | None = None, payload: dict | None = None):
        self.con.execute(
            'INSERT INTO event_log(created_at,session_id,event_name,content_id,payload_json) VALUES (?,?,?,?,?)',
            (datetime.now(timezone.utc).isoformat(), session_id, event_name, content_id, json.dumps(payload or {}, ensure_ascii=False)),
        )
        self.con.commit()

    def count(self) -> int:
        return int(self.con.execute('SELECT COUNT(*) FROM event_log').fetchone()[0])
