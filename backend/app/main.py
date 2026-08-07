"""FixPilot 后端入口：FastAPI + 认证 + 邀请码 + 纯 RAG 聊天。"""
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, db, service
from .knowledge import load_chunks

app = FastAPI(title="FixPilot", description="电脑故障排查 AI 助手")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

_chunks = load_chunks()
db.init_db()
auth.bootstrap_admin()


# ---------- 请求模型 ----------

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    convId: Optional[str] = None


class TitleRequest(BaseModel):
    question: str
    convId: Optional[str] = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class InviteLoginRequest(BaseModel):
    code: str


class InvitePinRequest(BaseModel):
    code: str
    pin: str


class InviteCreateRequest(BaseModel):
    quota: int = 50          # 次数，-1 表示不限
    hours: Optional[int] = None   # 有效期小时数，None 表示长期
    note: str = ""
    count: int = 1           # 一次生成几个


class InviteUpdateRequest(BaseModel):
    addQuota: int = 0        # 追加次数
    addHours: Optional[int] = None  # 追加有效期小时数


class NewConvRequest(BaseModel):
    title: str = "新对话"


# ---------- 工具函数 ----------

def _get_token(authorization: str) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip()


def _require_auth(authorization: Optional[str]) -> dict:
    token = _get_token(authorization or "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = auth.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return payload


def _require_admin(authorization: Optional[str]) -> dict:
    payload = _require_auth(authorization)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return payload


def _owner(payload: dict) -> str:
    """会话归属键：邀请码用户按 code，管理员按 username。"""
    if payload.get("role") == "admin":
        return "admin:" + payload.get("username", "admin")
    return payload.get("code", "")


# ---------- 健康检查 ----------

@app.get("/api/health")
def health():
    return {"status": "ok", "chunks": len(_chunks)}


# ---------- 认证 ----------

@app.post("/api/auth/admin-login")
def admin_login(req: AdminLoginRequest):
    admin = db.get_admin(req.username)
    if not admin or not auth.verify_password(req.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    token = auth.make_token({"role": "admin", "username": admin["username"]})
    return {"token": token, "role": "admin", "username": admin["username"]}


@app.post("/api/auth/invite-login")
def invite_login(req: InviteLoginRequest):
    code = (req.code or "").strip().upper()
    invite = db.get_invite(code)
    if not invite:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    ok, reason = auth.can_use(invite)
    if not ok:
        if reason == "expired":
            raise HTTPException(status_code=403, detail="邀请码已过期")
        raise HTTPException(status_code=403, detail="邀请码次数已用完，请联系管理员")
    # 返回 PIN 状态：mode=set 表示首次需设置 PIN，enter 表示需输入 PIN
    mode = "set" if not invite.get("pin_hash") else "enter"
    return {"status": "need_pin", "mode": mode, "code": code}


@app.post("/api/auth/invite-pin")
def invite_pin(req: InvitePinRequest):
    code = (req.code or "").strip().upper()
    pin = (req.pin or "").strip()
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN 码需为 4 位数字")
    invite = db.get_invite(code)
    if not invite:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    ok, reason = auth.can_use(invite)
    if not ok:
        if reason == "expired":
            raise HTTPException(status_code=403, detail="邀请码已过期")
        raise HTTPException(status_code=403, detail="邀请码次数已用完，请联系管理员")

    if invite.get("pin_hash"):
        # 已有 PIN：校验
        if not auth.verify_pin(pin, invite["pin_hash"]):
            raise HTTPException(status_code=401, detail="PIN 码错误")
    else:
        # 首次：设置 PIN
        db.set_pin(code, auth.hash_pin(pin))

    token = auth.make_token({"role": "user", "code": code})
    db.record_login(code)
    invite = db.get_invite(code)
    return {"token": token, "role": "user", "code": code,
            "quota_used": invite["quota_used"], "quota_total": invite["quota_total"],
            "expires_at": invite["expires_at"], "last_login_at": invite.get("last_login_at")}


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    if payload.get("role") == "admin":
        return {"role": "admin", "username": payload.get("username")}
    code = payload.get("code", "")
    invite = db.get_invite(code)
    if not invite:
        raise HTTPException(status_code=401, detail="邀请码不存在")
    ok, reason = auth.can_use(invite)
    return {"role": "user", "code": code,
            "quota_used": invite["quota_used"], "quota_total": invite["quota_total"],
            "expires_at": invite["expires_at"],
            "last_login_at": invite.get("last_login_at"),
            "can_use": ok, "reason": reason,
            "note": invite.get("note")}


# ---------- 管理员：邀请码管理 ----------

@app.post("/api/admin/invites")
def create_invites(req: InviteCreateRequest, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    expires_at = None
    if req.hours:
        import datetime as dt
        expires_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=req.hours)).isoformat()
    codes = []
    for _ in range(max(1, min(req.count, 50))):
        code = secrets.token_hex(3).upper()
        db.create_invite(code, req.quota, expires_at, req.note)
        codes.append({"code": code, "quota_total": req.quota, "expires_at": expires_at, "note": req.note})
    return {"codes": codes}


@app.get("/api/admin/invites")
def list_invites_admin(authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    invites = db.list_invites()
    for iv in invites:
        iv["expired"] = auth.is_expired(iv)
        iv["remaining"] = -1 if iv["quota_total"] == -1 else max(0, iv["quota_total"] - iv["quota_used"])
        # 已使用 = 有使用次数 或 曾经登录过
        iv["used"] = bool(iv["quota_used"] > 0 or iv.get("last_login_at"))
    return {"invites": invites}


@app.post("/api/admin/invites/{code}/update")
def update_invite(code: str, req: InviteUpdateRequest, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    invite = db.get_invite(code)
    if not invite:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    new_quota = invite["quota_total"]
    if req.addQuota:
        new_quota = -1 if new_quota == -1 else new_quota + req.addQuota
    new_exp = invite["expires_at"]
    if req.addHours:
        import datetime as dt
        base = dt.datetime.fromisoformat(new_exp) if new_exp else dt.datetime.now(dt.timezone.utc)
        new_exp = (base + dt.timedelta(hours=req.addHours)).isoformat()
    db.update_invite(code, quota_total=new_quota, expires_at=new_exp)
    iv = db.get_invite(code)
    return {"ok": True, "quota_total": iv["quota_total"], "expires_at": iv["expires_at"]}


@app.delete("/api/admin/invites/{code}")
def delete_invite(code: str, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    db.delete_invite(code)
    return {"ok": True}


@app.get("/api/admin/invites/{code}/conversations")
def invite_conversations(code: str, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    convs = db.list_conversations(code)
    result = []
    for c in convs:
        msgs = db.list_messages(c["id"])
        result.append({"conv": c, "messages": msgs})
    return {"code": code, "conversations": result}


# ---------- 对话（需登录） ----------

@app.get("/api/conversations")
def list_conv(authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    if payload.get("role") not in ("user", "admin"):
        raise HTTPException(status_code=403, detail="无权限")
    return {"conversations": db.list_conversations(_owner(payload))}


@app.post("/api/conversations")
def new_conv(req: NewConvRequest, authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    if payload.get("role") not in ("user", "admin"):
        raise HTTPException(status_code=403, detail="无权限")
    conv_id = "c" + secrets.token_hex(8)
    db.create_conversation(conv_id, _owner(payload), req.title)
    return {"id": conv_id}


@app.get("/api/conversations/{conv_id}/messages")
def conv_messages(conv_id: str, authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    conv = db.get_conversation(conv_id)
    if not conv or conv["invite_code"] != _owner(payload):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"messages": db.list_messages(conv_id)}


@app.delete("/api/conversations/{conv_id}")
def delete_conv(conv_id: str, authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    conv = db.get_conversation(conv_id)
    if not conv or conv["invite_code"] != _owner(payload):
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete_conversation(conv_id)
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/share")
def share_conv(conv_id: str, authorization: Optional[str] = Header(None)):
    """为会话生成（或复用）只读分享链接。"""
    payload = _require_auth(authorization)
    conv = db.get_conversation(conv_id)
    if not conv or conv["invite_code"] != _owner(payload):
        raise HTTPException(status_code=404, detail="会话不存在")
    token = conv.get("share_token")
    if not token:
        token = secrets.token_urlsafe(12)
        db.set_share_token(conv_id, token)
    url = f"/share/{token}"
    return {"token": token, "url": url}


@app.get("/api/share/{token}")
def get_shared(token: str):
    """公开接口：凭 token 返回对话内容（只读）。"""
    conv = db.get_conv_by_share(token)
    if not conv:
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")
    msgs = db.list_messages(conv["id"])
    return {"title": conv.get("title") or "对话", "created_at": conv.get("created_at"),
            "messages": msgs}


@app.post("/api/title")
def title(req: TitleRequest, authorization: Optional[str] = Header(None)):
    t = (req.question or "").strip()
    if not t:
        title = "新对话"
    else:
        title = t[:12]
    if req.convId:
        db.update_conversation_title(req.convId, title)
    return {"title": title}


@app.post("/api/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    role = payload.get("role")
    if role not in ("user", "admin"):
        raise HTTPException(status_code=403, detail="无权限")
    owner = _owner(payload)
    code = payload.get("code") if role == "user" else None

    # 配额检查（仅邀请码用户）
    if role == "user":
        invite = db.get_invite(code)
        if not invite:
            raise HTTPException(status_code=401, detail="邀请码不存在")
        ok, reason = auth.can_use(invite)
        if not ok:
            raise HTTPException(status_code=402, detail="邀请码次数已用完，请联系管理员")

    # 校验会话归属
    conv_id = req.convId
    if conv_id:
        conv = db.get_conversation(conv_id)
        if not conv or conv["invite_code"] != owner:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conv_id = "c" + secrets.token_hex(8)
        db.create_conversation(conv_id, owner)

    def gen():
        yield "data:__start__\n\n"
        acc = []
        try:
            for token in service.chat_stream(req.messages):
                acc.append(token)
                yield f"data: {token}\n\n"
        except Exception as e:
            yield f"data: __error__:{e}\n\n"
            return
        # 成功完成后：写库 + 扣配额（仅邀请码用户）
        user_text = _content_to_text(req.messages[-1].get("content")) if req.messages else ""
        db.add_message(conv_id, "user", user_text)
        db.add_message(conv_id, "assistant", "".join(acc).replace("[JOKE6]", "").strip())
        if role == "user":
            db.increment_quota_used(code)
        yield "data:__end__\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


# ---------- 只读分享页 ----------
@app.get("/share/{token}", response_class=HTMLResponse)
def share_page(token: str):
    f = STATIC_DIR / "share.html"
    return f.read_text(encoding="utf-8") if f.exists() else "share.html not found"


# 前端静态资源（必须放在 API 路由之后挂载）
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")