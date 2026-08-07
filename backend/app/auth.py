"""认证与授权：管理员登录、邀请码登录、token 校验。"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import config, db


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(calc, digest)


def hash_pin(pin: str) -> str:
    """哈希 4 位 PIN 码，返回 salt$digest。"""
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    calc = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(calc, digest)


# 签名 token：payload.signature，payload 为 base64url(json)
_TOKEN_SECRET = os.getenv("FIXPILOT_TOKEN_SECRET", secrets.token_hex(32))


def _b64e(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(data: str) -> bytes:
    import base64
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def make_token(payload: dict, ttl: int = None) -> str:
    import json
    ttl = ttl or config.TOKEN_TTL
    exp = int((datetime.now(timezone.utc) + timedelta(seconds=ttl)).timestamp())
    body = payload | {"exp": exp}
    raw = json.dumps(body, separators=(",", ":")).encode()
    payload_b64 = _b64e(raw)
    sig = hmac.new(_TOKEN_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token: str) -> Optional[dict]:
    import json
    try:
        payload_b64, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    expect = hmac.new(_TOKEN_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expect):
        return None
    try:
        body = json.loads(_b64d(payload_b64))
    except Exception:
        return None
    if body.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
        return None
    return body


def is_expired(invite: dict) -> bool:
    exp = invite.get("expires_at")
    if not exp:
        return False
    try:
        exp_dt = datetime.fromisoformat(exp)
    except ValueError:
        return False
    return datetime.now(timezone.utc) > exp_dt


def can_use(invite: dict) -> tuple:
    """返回 (ok, reason)。检查次数与有效期。"""
    if is_expired(invite):
        return False, "expired"
    qt = invite.get("quota_total")
    if qt is not None and qt != -1 and invite.get("quota_used", 0) >= qt:
        return False, "exhausted"
    return True, "ok"


def bootstrap_admin():
    """首次启动创建管理员。"""
    if db.get_admin(config.ADMIN_USERNAME) is None:
        db.create_admin(config.ADMIN_USERNAME, hash_password(config.ADMIN_PASSWORD))