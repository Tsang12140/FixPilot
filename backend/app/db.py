"""SQLite 数据层：管理员、邀请码、会话、消息。"""
import json
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
    conn.execute("PRAGMA journal_mode = WAL")
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

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,      -- 账号名，小写存储
                password_hash TEXT NOT NULL,       -- salt$digest，与 admin 同算法
                invite_code TEXT UNIQUE NOT NULL,  -- 一对一绑定邀请码
                created_at TEXT NOT NULL,
                FOREIGN KEY (invite_code) REFERENCES invite_codes(code)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                invite_code TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '新对话',
                share_token TEXT,
                avatar INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                image TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conv_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_api_settings (
                owner_key TEXT PRIMARY KEY,
                api_key TEXT NOT NULL DEFAULT '',
                api_base TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                models TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT 'deepseek',
                active_source TEXT NOT NULL DEFAULT 'platform',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                owner_key TEXT PRIMARY KEY,
                technical_level TEXT NOT NULL DEFAULT 'unknown',
                technical_level_source TEXT NOT NULL DEFAULT 'inferred_pending',
                technical_confidence TEXT NOT NULL DEFAULT 'low',
                response_style TEXT NOT NULL DEFAULT 'normal',
                onboarding_completed INTEGER NOT NULL DEFAULT 0,
                onboarding_seen INTEGER NOT NULL DEFAULT 0,
                onboarding_nudge_shown INTEGER NOT NULL DEFAULT 0,
                level_notice_shown INTEGER NOT NULL DEFAULT 0,
                level_notice_pending INTEGER NOT NULL DEFAULT 0,
                profiling_valid_turns INTEGER NOT NULL DEFAULT 0,
                beginner_score INTEGER NOT NULL DEFAULT 0,
                intermediate_score INTEGER NOT NULL DEFAULT 0,
                advanced_score INTEGER NOT NULL DEFAULT 0,
                profiling_evidence_types TEXT NOT NULL DEFAULT '[]',
                opposite_strong_signals INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
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
    if "avatar" not in ccols:
        conn.execute("ALTER TABLE conversations ADD COLUMN avatar INTEGER DEFAULT 1")
    # messages
    mcols = {r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
    if "image" not in mcols:
        conn.execute("ALTER TABLE messages ADD COLUMN image TEXT")
    # user_api_settings
    ucols = {r[1] for r in conn.execute("PRAGMA table_info(user_api_settings)").fetchall()}
    if "models" not in ucols:
        conn.execute("ALTER TABLE user_api_settings ADD COLUMN models TEXT NOT NULL DEFAULT ''")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- 用户回答偏好 / 技术水平画像 ----------

_PROFILE_FIELDS = (
    "technical_level", "technical_level_source", "technical_confidence", "response_style",
    "onboarding_completed", "onboarding_seen", "onboarding_nudge_shown",
    "level_notice_shown", "level_notice_pending", "profiling_valid_turns",
    "beginner_score", "intermediate_score", "advanced_score", "profiling_evidence_types",
    "opposite_strong_signals", "updated_at",
)


def _create_profile(conn: sqlite3.Connection, owner_key: str) -> None:
    conn.execute("INSERT OR IGNORE INTO user_profiles (owner_key, updated_at) VALUES (?, ?)", (owner_key, _now()))


def _get_profile(conn: sqlite3.Connection, owner_key: str) -> dict:
    _create_profile(conn, owner_key)
    row = conn.execute("SELECT * FROM user_profiles WHERE owner_key = ?", (owner_key,)).fetchone()
    profile = dict(row)
    try:
        profile["profiling_evidence_types"] = json.loads(profile["profiling_evidence_types"] or "[]")
    except json.JSONDecodeError:
        profile["profiling_evidence_types"] = []
    return profile


def _save_profile(conn: sqlite3.Connection, owner_key: str, profile: dict) -> dict:
    profile = dict(profile)
    profile["updated_at"] = _now()
    profile["profiling_evidence_types"] = json.dumps(profile.get("profiling_evidence_types") or [], ensure_ascii=False)
    assignments = ", ".join(f"{field} = ?" for field in _PROFILE_FIELDS)
    conn.execute("UPDATE user_profiles SET " + assignments + " WHERE owner_key = ?", [profile.get(field) for field in _PROFILE_FIELDS] + [owner_key])
    profile["profiling_evidence_types"] = json.loads(profile["profiling_evidence_types"])
    return profile


def get_profile(owner_key: str) -> dict:
    with _lock, _connect() as conn:
        return _get_profile(conn, owner_key)


def update_profile_preferences(owner_key: str, technical_level: Optional[str] = None,
                               response_style: Optional[str] = None,
                               onboarding_completed: Optional[bool] = None,
                               onboarding_seen: Optional[bool] = None) -> dict:
    """保存用户显式偏好。显式设置始终覆盖自动画像。"""
    with _lock, _connect() as conn:
        profile = _get_profile(conn, owner_key)
        if technical_level is not None:
            profile.update({
                "technical_level": technical_level,
                "technical_level_source": "explicit" if technical_level != "unknown" else "inferred_pending",
                "technical_confidence": "high" if technical_level != "unknown" else "low",
                "profiling_valid_turns": 0, "beginner_score": 0, "intermediate_score": 0,
                "advanced_score": 0, "profiling_evidence_types": [], "opposite_strong_signals": 0,
                "level_notice_shown": 0, "level_notice_pending": 0,
            })
        if response_style is not None:
            profile["response_style"] = response_style
        if onboarding_completed is not None:
            profile["onboarding_completed"] = int(onboarding_completed)
        if onboarding_seen is not None:
            profile["onboarding_seen"] = int(onboarding_seen)
        return _save_profile(conn, owner_key, profile)


def mark_onboarding_nudge(owner_key: str) -> dict:
    with _lock, _connect() as conn:
        profile = _get_profile(conn, owner_key)
        profile["onboarding_seen"] = 1
        profile["onboarding_nudge_shown"] = 1
        return _save_profile(conn, owner_key, profile)


def record_profile_signal(owner_key: str, signal: dict) -> dict:
    """记录判定器的结构化证据；显式选择永远不被覆盖。"""
    from .profiling import apply_signal
    with _lock, _connect() as conn:
        profile = _get_profile(conn, owner_key)
        if profile["technical_level_source"] == "explicit":
            return profile
        return _save_profile(conn, owner_key, apply_signal(profile, signal))


def mark_level_notice_shown(owner_key: str) -> dict:
    with _lock, _connect() as conn:
        profile = _get_profile(conn, owner_key)
        profile["level_notice_pending"] = 0
        profile["level_notice_shown"] = 1
        return _save_profile(conn, owner_key, profile)


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
        rows = conn.execute(
            """SELECT iv.*, u.username AS bound_username
               FROM invite_codes AS iv
               LEFT JOIN users AS u ON u.invite_code = iv.code
               ORDER BY iv.created_at DESC"""
        ).fetchall()
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


# ---------- 用户账号（账号密码绑定） ----------

def create_user(username: str, password_hash: str, invite_code: str) -> None:
    """创建用户账号并绑定到邀请码。username 应已规范化为小写。"""
    with _lock, _connect() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO users (username, password_hash, invite_code, created_at)
               VALUES (?, ?, ?, ?)""",
            (username, password_hash, invite_code, _now()),
        )


def get_user_by_username(username: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_invite_code(code: str) -> Optional[dict]:
    """用于判断某个邀请码是否已绑定账号。"""
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE invite_code = ?", (code,)).fetchone()
        return dict(row) if row else None


def update_user_password(username: str, password_hash: str) -> None:
    """修改用户密码。"""
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (password_hash, username),
        )


# ---------- 用户自定义 API 配置（按账号/邀请码粒度，跟随 owner_key） ----------

def _parse_models(raw: str, fallback_model: str = "") -> List[str]:
    """把 models 列（JSON 数组字符串）解析为列表；空/非法时退化为单模型。"""
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                models = [str(m).strip() for m in parsed if str(m).strip()]
                if models:
                    return models
        except (ValueError, TypeError):
            pass
    return [fallback_model] if fallback_model else []


def get_api_settings(owner_key: str) -> dict:
    """读取某账号的 API 配置，无记录时返回默认空配置。"""
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM user_api_settings WHERE owner_key = ?", (owner_key,)
        ).fetchone()
        if row:
            data = dict(row)
        else:
            data = {
                "owner_key": owner_key, "api_key": "", "api_base": "",
                "model": "", "models": "", "provider": "deepseek", "active_source": "platform",
                "updated_at": _now(),
            }
        data["models"] = _parse_models(data.get("models", ""), data.get("model", ""))
        return data


def save_api_settings(owner_key: str, api_key: str = "", api_base: str = "",
                      model: str = "", provider: str = "deepseek",
                      active_source: str = "platform",
                      models: Optional[List[str]] = None) -> dict:
    """保存某账号的 API 配置（upsert）。models 为完整模型列表（JSON 存储），model 为当前激活。"""
    existing = get_api_settings(owner_key)
    if models is None:
        models = existing.get("models") or ([existing.get("model")] if existing.get("model") else [])
    models = [str(m).strip() for m in models if str(m).strip()]
    if not model and models:
        model = models[0]
    models_json = json.dumps(models, ensure_ascii=False)
    with _lock, _connect() as conn:
        conn.execute(
            """INSERT INTO user_api_settings
               (owner_key, api_key, api_base, model, models, provider, active_source, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
             ON CONFLICT(owner_key) DO UPDATE SET
               api_key = excluded.api_key,
               api_base = excluded.api_base,
               model = excluded.model,
               models = excluded.models,
               provider = excluded.provider,
               active_source = excluded.active_source,
               updated_at = excluded.updated_at""",
            (owner_key, api_key, api_base, model, models_json, provider, active_source, _now()),
        )
    return {
        "owner_key": owner_key, "api_key": api_key, "api_base": api_base,
        "model": model, "models": models, "provider": provider, "active_source": active_source,
    }


def clear_api_settings(owner_key: str) -> dict:
    """清空某账号的 API 配置（删除记录，回到平台 API）。"""
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM user_api_settings WHERE owner_key = ?", (owner_key,))
    return {
        "owner_key": owner_key, "api_key": "", "api_base": "", "model": "",
        "models": [], "provider": "deepseek", "active_source": "platform",
    }


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


def search_conversations(code: str, query: str) -> List[dict]:
    """Search one owner's conversation titles and message text."""
    text = (query or "").strip()
    if not text:
        return list_conversations(code)
    escaped = text.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    pattern = f"%{escaped}%"
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.*
            FROM conversations AS c
            WHERE c.invite_code = ?
              AND (
                c.title LIKE ? ESCAPE '!'
                OR EXISTS (
                    SELECT 1
                    FROM messages AS m
                    WHERE m.conv_id = c.id
                      AND m.content LIKE ? ESCAPE '!'
                )
              )
            ORDER BY c.created_at DESC
            """,
            (code, pattern, pattern),
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


def set_share_token(conv_id: str, token: str, avatar: int = 1) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE conversations SET share_token = ?, avatar = ? WHERE id = ?",
            (token, avatar, conv_id),
        )


def get_conv_by_share(token: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE share_token = ?", (token,)).fetchone()
        return dict(row) if row else None


def add_message(conv_id: str, role: str, content: str, image: Optional[str] = None) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO messages (conv_id, role, content, image, created_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, role, content, image, _now()),
        )


def list_messages(conv_id: str) -> List[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conv_id = ? ORDER BY id ASC",
            (conv_id,),
        ).fetchall()
        return [dict(r) for r in rows]