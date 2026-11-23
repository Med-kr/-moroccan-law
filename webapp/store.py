"""Local storage of the web app: users, settings, conversations, uploaded documents, audit log.

Everything stays on the machine that runs the app (SQLite file in the data folder).
- Conversation contents, uploaded documents and the AI provider key are encrypted at rest with a
  key kept in <data>/secret.key (mode 600), or given in MOROCCAN_LAW_SECRET (Fernet key).
- Passwords: PBKDF2-SHA256, 600,000 iterations, per-user salt.
- Audit log: who did what and when (login, question asked, document uploaded, export, deletion) —
  never the content itself.
- Retention: conversations and documents older than `retention_days` are deleted.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading

from cryptography.fernet import Fernet, InvalidToken

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, role TEXT NOT NULL,
  salt BLOB NOT NULL, pw BLOB NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title BLOB NOT NULL,
  messages BLOB NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name BLOB NOT NULL,
  text BLOB NOT NULL, refs TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, ref BLOB NOT NULL,
  text BLOB NOT NULL, articles TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at TEXT NOT NULL, user TEXT, action TEXT NOT NULL, detail TEXT);
"""
PBKDF2_ROUNDS = 600_000


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, data_dir: str):
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir
        self.fernet = Fernet(self._key())
        self.db = sqlite3.connect(os.path.join(data_dir, "moroccan-law.db"), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript(SCHEMA)
            self.db.commit()

    # ---------------------------------------------------------------- encryption
    def _key(self) -> bytes:
        env = os.environ.get("MOROCCAN_LAW_SECRET")
        if env:
            return env.encode()
        path = os.path.join(self.data_dir, "secret.key")
        if not os.path.exists(path):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(Fernet.generate_key())
        with open(path, "rb") as fh:
            return fh.read().strip()

    def enc(self, text: str) -> bytes:
        return self.fernet.encrypt(text.encode("utf-8"))

    def dec(self, blob: bytes) -> str:
        try:
            return self.fernet.decrypt(blob).decode("utf-8")
        except InvalidToken:
            return ""

    def q(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur.fetchall()

    # ---------------------------------------------------------------- users
    @staticmethod
    def _hash(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)

    def has_users(self) -> bool:
        return bool(self.q("SELECT 1 FROM users LIMIT 1"))

    def add_user(self, name: str, password: str, role: str = "member") -> None:
        if len(password) < 10:
            raise ValueError("password must have at least 10 characters")
        if role not in ("admin", "member"):
            raise ValueError("role is admin or member")
        salt = secrets.token_bytes(16)
        self.q("INSERT INTO users (name, role, salt, pw, created) VALUES (?,?,?,?,?)",
               (name, role, salt, self._hash(password, salt), now()))

    def users(self) -> list[dict]:
        return [{"id": r["id"], "name": r["name"], "role": r["role"], "created": r["created"]}
                for r in self.q("SELECT id, name, role, created FROM users ORDER BY id")]

    def delete_user(self, user_id: int) -> None:
        self.q("DELETE FROM sessions WHERE user_id=?", (user_id,))
        self.q("DELETE FROM users WHERE id=?", (user_id,))

    def login(self, name: str, password: str) -> str | None:
        rows = self.q("SELECT * FROM users WHERE name=?", (name,))
        if not rows or not hmac.compare_digest(rows[0]["pw"], self._hash(password, rows[0]["salt"])):
            return None
        token = secrets.token_urlsafe(32)
        expires = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=12)).isoformat()
        self.q("INSERT INTO sessions VALUES (?,?,?)", (token, rows[0]["id"], expires))
        return token

    def user_for(self, token: str | None) -> dict | None:
        if not token:
            return None
        rows = self.q("SELECT u.id, u.name, u.role, s.expires FROM sessions s JOIN users u ON u.id=s.user_id "
                      "WHERE s.token=?", (token,))
        if not rows or rows[0]["expires"] < now():
            return None
        return {"id": rows[0]["id"], "name": rows[0]["name"], "role": rows[0]["role"]}

    def logout(self, token: str) -> None:
        self.q("DELETE FROM sessions WHERE token=?", (token,))

    # ---------------------------------------------------------------- settings (encrypted)
    def set_setting(self, key: str, value) -> None:
        self.q("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (key, self.enc(json.dumps(value))))

    def setting(self, key: str, default=None):
        rows = self.q("SELECT value FROM settings WHERE key=?", (key,))
        if not rows:
            return default
        raw = self.dec(rows[0]["value"])
        return json.loads(raw) if raw else default

    # ---------------------------------------------------------------- conversations
    def save_conversation(self, user_id: int, conv_id: int | None, title: str, messages: list) -> int:
        blob = self.enc(json.dumps(messages, ensure_ascii=False))
        if conv_id:
            self.q("UPDATE conversations SET messages=?, updated=? WHERE id=? AND user_id=?",
                   (blob, now(), conv_id, user_id))
            return conv_id
        with self.lock:
            cur = self.db.execute("INSERT INTO conversations (user_id, title, messages, created, updated) VALUES (?,?,?,?,?)",
                                  (user_id, self.enc(title[:120]), blob, now(), now()))
            self.db.commit()
            return cur.lastrowid

    def conversations(self, user_id: int) -> list[dict]:
        return [{"id": r["id"], "title": self.dec(r["title"]), "updated": r["updated"]}
                for r in self.q("SELECT id, title, updated FROM conversations WHERE user_id=? ORDER BY updated DESC",
                                (user_id,))]

    def conversation(self, user_id: int, conv_id: int) -> list | None:
        rows = self.q("SELECT messages FROM conversations WHERE id=? AND user_id=?", (conv_id, user_id))
        return json.loads(self.dec(rows[0]["messages"]) or "[]") if rows else None

    def delete_conversation(self, user_id: int, conv_id: int) -> None:
        self.q("DELETE FROM conversations WHERE id=? AND user_id=?", (conv_id, user_id))

    # ---------------------------------------------------------------- documents and decisions
    def save_document(self, user_id: int, name: str, text: str, refs: list) -> int:
        with self.lock:
            cur = self.db.execute("INSERT INTO documents (user_id, name, text, refs, created) VALUES (?,?,?,?,?)",
                                  (user_id, self.enc(name), self.enc(text), json.dumps(refs, ensure_ascii=False), now()))
            self.db.commit()
            return cur.lastrowid

    def document(self, user_id: int, doc_id: int) -> dict | None:
        rows = self.q("SELECT * FROM documents WHERE id=? AND user_id=?", (doc_id, user_id))
        if not rows:
            return None
        r = rows[0]
        return {"id": r["id"], "name": self.dec(r["name"]), "text": self.dec(r["text"]), "refs": json.loads(r["refs"])}

    def documents(self, user_id: int) -> list[dict]:
        return [{"id": r["id"], "name": self.dec(r["name"]), "created": r["created"], "refs": json.loads(r["refs"])}
                for r in self.q("SELECT id, name, refs, created FROM documents WHERE user_id=? ORDER BY id DESC", (user_id,))]

    def delete_document(self, user_id: int, doc_id: int) -> None:
        self.q("DELETE FROM documents WHERE id=? AND user_id=?", (doc_id, user_id))

    def save_decision(self, user_id: int, ref: str, text: str, articles: list) -> int:
        with self.lock:
            cur = self.db.execute("INSERT INTO decisions (user_id, ref, text, articles, created) VALUES (?,?,?,?,?)",
                                  (user_id, self.enc(ref), self.enc(text), json.dumps(articles, ensure_ascii=False), now()))
            self.db.commit()
            return cur.lastrowid

    def decisions(self, user_id: int) -> list[dict]:
        return [{"id": r["id"], "ref": self.dec(r["ref"]), "text": self.dec(r["text"]), "articles": json.loads(r["articles"]),
                 "created": r["created"]}
                for r in self.q("SELECT * FROM decisions WHERE user_id=? ORDER BY id DESC", (user_id,))]

    def delete_decision(self, user_id: int, dec_id: int) -> None:
        self.q("DELETE FROM decisions WHERE id=? AND user_id=?", (dec_id, user_id))

    # ---------------------------------------------------------------- audit and retention
    def audit(self, user: str | None, action: str, detail: str = "") -> None:
        self.q("INSERT INTO audit (at, user, action, detail) VALUES (?,?,?,?)", (now(), user, action, detail[:200]))

    def audit_log(self, limit: int = 500) -> list[dict]:
        return [dict(r) for r in self.q("SELECT at, user, action, detail FROM audit ORDER BY id DESC LIMIT ?", (limit,))]

    def purge(self, days: int) -> int:
        if days <= 0:
            return 0
        cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat(timespec="seconds")
        n = 0
        for table, col in (("conversations", "updated"), ("documents", "created")):
            n += len(self.q(f"SELECT id FROM {table} WHERE {col} < ?", (cutoff,)))
            self.q(f"DELETE FROM {table} WHERE {col} < ?", (cutoff,))
        self.q("DELETE FROM sessions WHERE expires < ?", (now(),))
        return n


def new_secret() -> str:
    """A key to put in MOROCCAN_LAW_SECRET (for instance in a Docker secret)."""
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    print(new_secret())
