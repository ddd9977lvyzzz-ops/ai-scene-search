from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any


DDL = """
CREATE TABLE IF NOT EXISTS users(
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_sessions(
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE TABLE IF NOT EXISTS watchlist(
    user_id TEXT NOT NULL,
    content_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id, content_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE TABLE IF NOT EXISTS saved_scenes(
    user_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'private',
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id, scene_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class UserStore:
    """Portfolio-grade passwordless demo identity.

    This is intentionally not a password implementation. Production should swap this layer for
    OAuth/OIDC or verified email/phone OTP while preserving the user/watchlist interfaces.
    """

    def __init__(self, path: str):
        self.con=sqlite3.connect(path,check_same_thread=False)
        self.con.row_factory=sqlite3.Row
        self.con.executescript(DDL)
        self.con.commit()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def login_or_register(self, email: str, display_name: str, ttl_days: int=30) -> dict[str,Any]:
        email=email.strip().casefold()
        display_name=display_name.strip()[:40]
        if not email or "@" not in email or not display_name:
            raise ValueError("invalid_identity")
        now=_now()
        row=self.con.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if row:
            user_id=row["user_id"]
            self.con.execute("UPDATE users SET display_name=?,updated_at=? WHERE user_id=?",(display_name,_iso(now),user_id))
        else:
            user_id="usr_"+secrets.token_urlsafe(12)
            self.con.execute(
                "INSERT INTO users(user_id,email,display_name,created_at,updated_at) VALUES (?,?,?,?,?)",
                (user_id,email,display_name,_iso(now),_iso(now))
            )
        token=secrets.token_urlsafe(32)
        self.con.execute(
            "INSERT INTO auth_sessions(token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)",
            (self._hash_token(token),user_id,_iso(now),_iso(now+timedelta(days=ttl_days)))
        )
        self.con.commit()
        return {"token":token,"user":self.get_user(user_id),"auth_mode":"demo_passwordless"}

    def user_for_token(self, token: str) -> dict[str,Any] | None:
        if not token:return None
        row=self.con.execute("""
          SELECT u.* FROM auth_sessions s JOIN users u ON u.user_id=s.user_id
          WHERE s.token_hash=? AND s.expires_at>?
        """,(self._hash_token(token),_iso(_now()))).fetchone()
        return dict(row) if row else None

    def get_user(self,user_id: str) -> dict[str,Any] | None:
        row=self.con.execute("SELECT * FROM users WHERE user_id=?",(user_id,)).fetchone()
        return dict(row) if row else None

    def list_watchlist(self,user_id: str) -> list[str]:
        rows=self.con.execute("SELECT content_id FROM watchlist WHERE user_id=? ORDER BY created_at DESC",(user_id,)).fetchall()
        return [r["content_id"] for r in rows]

    def add_watchlist(self,user_id: str,content_id: str) -> None:
        self.con.execute(
            "INSERT OR IGNORE INTO watchlist(user_id,content_id,created_at) VALUES (?,?,?)",
            (user_id,content_id,_iso(_now()))
        );self.con.commit()

    def remove_watchlist(self,user_id: str,content_id: str) -> None:
        self.con.execute("DELETE FROM watchlist WHERE user_id=? AND content_id=?",(user_id,content_id));self.con.commit()

    def save_scene(self,user_id: str,scene_id: str,title: str,prompt: str,visibility: str="private") -> None:
        visibility=visibility if visibility in {"private","unlisted","public"} else "private"
        self.con.execute("""
          INSERT OR REPLACE INTO saved_scenes(user_id,scene_id,title,prompt,visibility,created_at)
          VALUES (?,?,?,?,?,?)
        """,(user_id,scene_id,title,prompt,visibility,_iso(_now())))
        self.con.commit()

    def list_scenes(self,user_id: str) -> list[dict[str,Any]]:
        return [dict(r) for r in self.con.execute(
            "SELECT scene_id,title,prompt,visibility,created_at FROM saved_scenes WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()]
