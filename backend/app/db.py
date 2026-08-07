"""SQLite 数据层：管理员、邀请码、会话、消息。"""
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "fixpilot.db"

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS admin (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invite_codes (
                code TEXT PRIMARY KEY,
                quota_total INTEGER NOT NULL,      -- 总可用次数，-1 表示不限
                quota_used INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT,                   -- ISO 时间，NULL 表示长期有效
                note TEXT,
                last_login_at TEXT,                -- 最近一次登录时间
                pin_hash TEXT,                     -- 4 位 PIN 码哈希，NULL 表示未设置
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                invite_code TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '新对话',
                share_token TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conv_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conv_id);
            CREATE INDEX IF NOT EXISTS idx_conv_code ON conversations(invite_code);
            """
        )
        _migrate(conn)


def _migrate(conn: sqlite3.Connection):
    """轻量迁移：为已存在的库补加缺失列。"""
    # invite_codes
    cols = {r[1] for r in conn.execute("PRAGMA table_info(invite_codes)").fetchall()}
    if "last_login_at" not in cols:
        conn.execute("ALTER TABLE invite_codes ADD COLUMN last_login_at TEXT")
    if "pin_hash" not in cols:
        conn.execute("ALTER TABLE invite_codes ADD COLUMN pin_hash TEXT")
    # conversations
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()}
    if "share_token" not in ccols:
        conn.execute("ALTER TABLE conversations ADD COLUMN share_token TEXT")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- 管理员 ----------

def get_admin(username: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def create_admin(username: str, password_hash: str):
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admin (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, _now()),
        )


# ---------- 邀请码 ----------

def create_invite(code: str, quota_total: int, expires_at: Optional[str], note: str = "") -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO invite_codes
               (code, quota_total, quota_used, expires_at, note, created_at)
               VALUES (?, ?, 0, ?, ?, ?)""",
            (code, quota_total, expires_at, note, _now()),
        )


def get_invite(code: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM invite_codes WHERE code = ?", (code,)).fetchone()
        return dict(row) if row else None


def list_invites() -> List[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM invite_codes ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_invite(code: str, quota_total: Optional[int] = None, expires_at: Optional[str] = None, note: Optional[str] = None) -> None:
    fields, values = [], []
    if quota_total is not None:
        fields.append("quota_total = ?")
        values.append(quota_total)
    if expires_at is not None:
        fields.append("expires_at = ?")
        values.append(expires_at)
    if note is not None:
        fields.append("note = ?")
        values.append(note)
    if not fields:
        return
    values.append(code)
    with _lock, _connect() as conn:
        conn.execute(f"UPDATE invite_codes SET {', '.join(fields)} WHERE code = ?", values)


def increment_quota_used(code: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("UPDATE invite_codes SET quota_used = quota_used + 1 WHERE code = ?", (code,))


def record_login(code: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("UPDATE invite_codes SET last_login_at = ? WHERE code = ?", (_now(), code))


def set_pin(code: str, pin_hash: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("UPDATE invite_codes SET pin_hash = ? WHERE code = ?", (pin_hash, code))


def delete_invite(code: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM invite_codes WHERE code = ?", (code,))


# ---------- 会话 / 消息 ----------

def create_conversation(conv_id: str, code: str, title: str = "新对话") -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, invite_code, title, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, code, title, _now()),
        )


def list_conversations(code: str) -> List[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE invite_code = ? ORDER BY created_at DESC",
            (code,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_conversation(conv_id: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        return dict(row) if row else None


def update_conversation_title(conv_id: str, title: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))


def delete_conversation(conv_id: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


def set_share_token(conv_id: str, token: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("UPDATE conversations SET share_token = ? WHERE id = ?", (token, conv_id))


def get_conv_by_share(token: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE share_token = ?", (token,)).fetchone()
        return dict(row) if row else None


def add_message(conv_id: str, role: str, content: str) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO messages (conv_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, _now()),
        )


def list_messages(conv_id: str) -> List[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conv_id = ? ORDER BY id ASC",
            (conv_id,),
        ).fetchall()
        return [dict(r) for r in rows]