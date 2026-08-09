"""FixPilot 后端入口：FastAPI + 认证 + 邀请码 + 纯 RAG 聊天。"""
import json
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import api_diagnostics, auth, config, db, llm, memes, profiling, safety, service
from .knowledge import load_chunks

app = FastAPI(title="FixPilot", description="电脑故障排查 AI 助手")


@app.middleware("http")
async def no_cache_static(request, call_next):
    """禁用前端静态资源的强缓存，避免改版后浏览器仍使用旧文件。"""
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".css", ".html", ".svg", ".png")):
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    return response

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MEME_DIR = Path(__file__).resolve().parents[2] / "file" / "img"

_chunks = load_chunks()
db.init_db()
auth.bootstrap_admin()


# ---------- 请求模型 ----------

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    convId: Optional[str] = None
    apiKey: Optional[str] = None       # 用户自带 API Key（有值则用自定义 API，跳过配额）
    apiBase: Optional[str] = None      # 自定义 API 基址（OpenAI 兼容）
    model: Optional[str] = None        # 自定义模型名


class ApiTestRequest(BaseModel):
    """Custom API connectivity tests do not require chat messages."""
    apiKey: str
    apiBase: Optional[str] = None
    model: Optional[str] = None


class TitleRequest(BaseModel):
    question: str
    convId: Optional[str] = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AccountLoginRequest(BaseModel):
    """账号密码登录：同时接受管理员账号和用户绑定账号。"""
    username: str
    password: str


class BindAccountRequest(BaseModel):
    """邀请码用户绑定账号密码。"""
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    """修改用户密码。"""
    oldPassword: str
    newPassword: str


class InviteLoginRequest(BaseModel):
    code: str


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


class ProfileUpdateRequest(BaseModel):
    technicalLevel: Optional[str] = None
    responseStyle: Optional[str] = None
    onboardingCompleted: Optional[bool] = None
    onboardingSeen: Optional[bool] = None

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

def _public_profile(profile: dict) -> dict:
    """只返回前端需要的偏好状态，不暴露内部评分细节。"""
    keys = (
        "technical_level", "technical_level_source", "technical_confidence", "response_style",
        "onboarding_completed", "onboarding_seen", "onboarding_nudge_shown",
        "level_notice_shown", "level_notice_pending", "profiling_valid_turns",
    )
    return {key: profile.get(key) for key in keys}


# ---------- 健康检查 ----------

@app.get("/api/health")
def health():
    return {"status": "ok", "chunks": len(_chunks)}


# ---------- 认证 ----------

@app.post("/api/auth/admin-login")
def admin_login(req: AdminLoginRequest):
    admin = db.get_admin((req.username or "").strip())
    if admin and not auth.admin_login_allowed(admin["username"]):
        raise HTTPException(status_code=429, detail="尝试次数过多，请稍后再试")
    if not admin or not auth.verify_password(req.password, admin["password_hash"]):
        if admin:
            auth.record_admin_login_failure(admin["username"])
        raise HTTPException(status_code=401, detail="账号或密码错误")
    auth.clear_admin_login_failures(admin["username"])
    token = auth.make_token({"role": "admin", "username": admin["username"]})
    return {"token": token, "role": "admin", "username": admin["username"]}


@app.post("/api/auth/account-login")
def account_login(req: AccountLoginRequest):
    """账号密码登录：同时接受管理员账号和用户绑定账号。"""
    username = (req.username or "").strip()
    # 1. Administrator
    admin = db.get_admin(username)
    if admin and not auth.admin_login_allowed(admin["username"]):
        raise HTTPException(status_code=429, detail="尝试次数过多，请稍后再试")
    if admin and auth.verify_password(req.password, admin["password_hash"]):
        auth.clear_admin_login_failures(admin["username"])
        token = auth.make_token({"role": "admin", "username": admin["username"]})
        return {"token": token, "role": "admin", "username": admin["username"]}
    if admin:
        auth.record_admin_login_failure(admin["username"])
    # 2. Bound invite user (usernames are stored lowercase).
    user = db.get_user_by_username(username.lower())
    if user and auth.verify_password(req.password, user["password_hash"]):
        token = auth.make_token({"role": "user", "username": user["username"], "code": user["invite_code"]})
        invite = db.get_invite(user["invite_code"])
        db.record_login(user["invite_code"])
        return {
            "token": token, "role": "user", "username": user["username"], "code": user["invite_code"],
            "quota_used": invite["quota_used"] if invite else 0,
            "quota_total": invite["quota_total"] if invite else 0,
            "expires_at": invite["expires_at"] if invite else None,
            "last_login_at": invite.get("last_login_at") if invite else None,
        }
    raise HTTPException(status_code=401, detail="账号或密码错误")


@app.post("/api/auth/bind-account")
def bind_account(req: BindAccountRequest, authorization: Optional[str] = Header(None)):
    """邀请码用户绑定账号密码。要求当前以邀请码登录（role=user）。"""
    payload = _require_auth(authorization)
    if payload.get("role") != "user":
        raise HTTPException(status_code=403, detail="仅邀请码用户可绑定账号")
    code = payload.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="会话无效，请重新登录")

    import re
    username = (req.username or "").strip().lower()
    if not re.match(r"^[a-z0-9_]{3,20}$", username):
        raise HTTPException(status_code=400, detail="账号需为 3-20 位字母/数字/下划线")
    password = req.password or ""
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    # 邀请码已绑定过
    if db.get_user_by_invite_code(code):
        raise HTTPException(status_code=409, detail="当前邀请码已绑定账号")
    # 用户名被占用
    # Reserve administrator names so an invite user cannot impersonate one.
    if db.get_admin(username) or db.get_user_by_username(username):
        raise HTTPException(status_code=409, detail="账号名不可用")

    db.create_user(username, auth.hash_password(password), code)
    return {"ok": True, "username": username}


@app.post("/api/user/change-password")
def change_password(req: ChangePasswordRequest, authorization: Optional[str] = Header(None)):
    """修改已绑定账号的密码。"""
    payload = _require_auth(authorization)
    if payload.get("role") != "user":
        raise HTTPException(status_code=403, detail="仅用户账号可修改密码")
    code = payload.get("code", "")
    user = db.get_user_by_invite_code(code)
    if not user:
        raise HTTPException(status_code=400, detail="请先绑定账号")
    if not auth.verify_password(req.oldPassword, user["password_hash"]):
        raise HTTPException(status_code=401, detail="原密码错误")
    if len(req.newPassword) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    db.update_user_password(user["username"], auth.hash_password(req.newPassword))
    return {"ok": True}


@app.post("/api/auth/invite-login")
def invite_login(req: InviteLoginRequest):
    code = (req.code or "").strip().upper()
    invite = db.get_invite(code)
    if not invite:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    ok, reason = auth.can_use(invite)
    # 允许登录（即使次数用完/过期），由前端根据 can_use 显示提示引导用户用自己的 API
    token = auth.make_token({"role": "user", "code": code})
    db.record_login(code)
    invite = db.get_invite(code)
    return {"token": token, "role": "user", "code": code,
            "quota_used": invite["quota_used"], "quota_total": invite["quota_total"],
            "expires_at": invite["expires_at"], "last_login_at": invite.get("last_login_at"),
            "can_use": ok, "reason": reason}


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    if payload.get("role") == "admin":
        return {"role": "admin", "username": payload.get("username"), "platform_model": config.DEEPSEEK_MODEL, "profile": _public_profile(db.get_profile(_owner(payload)))}
    code = payload.get("code", "")
    invite = db.get_invite(code)
    if not invite:
        raise HTTPException(status_code=401, detail="邀请码不存在")
    ok, reason = auth.can_use(invite)
    # 查询当前邀请码是否已绑定账号
    bound = db.get_user_by_invite_code(code)
    return {"role": "user", "code": code, "platform_model": config.DEEPSEEK_MODEL,
            "username": payload.get("username") or (bound["username"] if bound else None),
            "bound_username": bound["username"] if bound else None,
            "quota_used": invite["quota_used"], "quota_total": invite["quota_total"],
            "expires_at": invite["expires_at"],
            "last_login_at": invite.get("last_login_at"),
            "can_use": ok, "reason": reason,
            "note": invite.get("note"), "profile": _public_profile(db.get_profile(_owner(payload)))}


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

# ---------- 回答偏好 / 技术水平画像 ----------

@app.get("/api/profile")
def get_profile(authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    return {"profile": _public_profile(db.get_profile(_owner(payload)))}


@app.post("/api/profile/preferences")
def update_profile(req: ProfileUpdateRequest, authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    if req.technicalLevel is not None and req.technicalLevel not in {"unknown", "beginner", "intermediate", "advanced"}:
        raise HTTPException(status_code=400, detail="电脑水平参数无效")
    if req.responseStyle is not None and req.responseStyle not in {"normal", "roast", "concise"}:
        raise HTTPException(status_code=400, detail="说话方式参数无效")
    profile = db.update_profile_preferences(
        _owner(payload),
        technical_level=req.technicalLevel,
        response_style=req.responseStyle,
        onboarding_completed=req.onboardingCompleted,
        onboarding_seen=req.onboardingSeen,
    )
    return {"profile": _public_profile(profile)}


@app.post("/api/profile/onboarding-nudge")
def onboarding_nudge(authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    return {"profile": _public_profile(db.mark_onboarding_nudge(_owner(payload)))}

# ---------- 对话（需登录） ----------

@app.get("/api/conversations")
def list_conv(authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    if payload.get("role") not in ("user", "admin"):
        raise HTTPException(status_code=403, detail="无权限")
    return {"conversations": db.list_conversations(_owner(payload))}


@app.get("/api/conversations/search")
def search_conv(q: str = "", authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    if payload.get("role") not in ("user", "admin"):
        raise HTTPException(status_code=403, detail="无权限")
    return {"conversations": db.search_conversations(_owner(payload), q)}


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
def share_conv(conv_id: str, avatar: Optional[int] = None, authorization: Optional[str] = Header(None)):
    """为会话生成（或复用）只读分享链接。"""
    payload = _require_auth(authorization)
    conv = db.get_conversation(conv_id)
    if not conv or conv["invite_code"] != _owner(payload):
        raise HTTPException(status_code=404, detail="会话不存在")
    token = conv.get("share_token")
    if not token:
        token = secrets.token_urlsafe(12)
        db.set_share_token(conv_id, token, avatar or 1)
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
            "avatar": conv.get("avatar") or 1, "messages": msgs}


@app.post("/api/title")
def title(req: TitleRequest, authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    t = (req.question or "").strip()
    if not t:
        title = "新对话"
    else:
        title = t[:12]
    if req.convId:
        conv = db.get_conversation(req.convId)
        if not conv or conv["invite_code"] != _owner(payload):
            raise HTTPException(status_code=404, detail="会话不存在")
        db.update_conversation_title(req.convId, title)
    return {"title": title}


@app.post("/api/test-api")
def test_api(req: ApiTestRequest, authorization: Optional[str] = Header(None)):
    """Test a user-supplied API with a minimal compatible request."""
    _require_auth(authorization)
    endpoint = llm.api_endpoint_url(req.apiBase or "")
    protocol = "Responses API" if llm.is_responses_api_url(endpoint) else "Chat Completions"
    attempt_id = api_diagnostics.start("test", endpoint, req.model or "", req.apiKey)
    try:
        llm.test_chat_connection(
            api_key=req.apiKey,
            base_url=req.apiBase or "",
            model=req.model or "",
        )
        api_diagnostics.success(attempt_id)
        return {
            "ok": True,
            "protocol": protocol,
            "model": req.model or "default model",
            "diagnosticId": attempt_id,
        }
    except Exception as exc:
        api_diagnostics.failure(attempt_id, exc)
        raise HTTPException(status_code=400, detail=api_diagnostics.public_message(exc, attempt_id))


@app.post("/api/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    payload = _require_auth(authorization)
    role = payload.get("role")
    if role not in ("user", "admin"):
        raise HTTPException(status_code=403, detail="无权限")
    owner = _owner(payload)
    code = payload.get("code") if role == "user" else None
    try:
        client_messages = service.validate_client_messages(req.messages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    use_custom_api = bool(req.apiKey)
    if role == "user" and not use_custom_api:
        invite = db.get_invite(code)
        if not invite:
            raise HTTPException(status_code=401, detail="邀请码不存在")
        ok, reason = auth.can_use(invite)
        if not ok:
            detail = "使用期限已到，可在设置中填入自己的 API 继续使用" if reason == "expired" else "次数已用完，可在设置中填入自己的 API 继续使用"
            raise HTTPException(status_code=402, detail=detail)

    conv_id = req.convId
    if conv_id:
        conv = db.get_conversation(conv_id)
        if not conv or conv["invite_code"] != owner:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conv_id = "c" + secrets.token_hex(8)
        db.create_conversation(conv_id, owner)

    # 前端只提交本轮消息；这里补入已存会话，修复多轮问诊缺少上下文的问题。
    history = [
        {"role": item["role"], "content": item["content"]}
        for item in db.list_messages(conv_id)[-16:]
        if item.get("role") in {"user", "assistant"}
    ]
    chat_messages = history + client_messages
    normalized_messages = service.normalize_messages(chat_messages)
    latest_user_text = next(
        (item["content"] for item in reversed(normalized_messages) if item.get("role") == "user"), ""
    )
    profile_before = db.get_profile(owner)
    signal = profiling.classify_turn(latest_user_text) if profile_before.get("technical_level_source") != "explicit" else {}
    profile_for_reply = profiling.apply_signal(profile_before, signal) if signal else profile_before
    temporary = profiling.temporary_level(signal) if profile_for_reply.get("technical_level") == "unknown" else "unknown"
    notice_to_show = ""
    if profile_before.get("level_notice_pending") and not profile_before.get("level_notice_shown"):
        notice_to_show = profiling.profile_notice(profile_before.get("technical_level", "unknown"))

    def gen():
        yield "data:__start__\n\n"
        attempt_id = api_diagnostics.start("chat", req.apiBase or "", req.model or "", req.apiKey or "", conv_id=conv_id) if use_custom_api else api_diagnostics.start("chat", "", "", "", conv_id=conv_id)
        acc = []
        prefix = []
        effect = None
        effect_sent = False
        awaiting_directive = True
        preflight_risk_level = safety.infer_risk_level(latest_user_text)
        risk_seen = preflight_risk_level is not None
        if preflight_risk_level:
            yield f"data: __risk__:{json.dumps(safety.risk_notice(preflight_risk_level), ensure_ascii=False)}\n\n"
        try:
            for token in service.chat_stream(
                normalized_messages,
                api_key=req.apiKey or "",
                base_url=req.apiBase or "",
                model=req.model or "",
                profile=profile_for_reply,
                temporary_level=temporary,
                already_normalized=True,
            ):
                if awaiting_directive:
                    prefix.append(token)
                    prefix_text = "".join(prefix)
                    risk_level, risk_remainder = safety.parse_risk_directive(prefix_text)
                    if risk_level is not None:
                        if not risk_seen:
                            yield f"data: __risk__:{json.dumps(safety.risk_notice(risk_level), ensure_ascii=False)}\n\n"
                        risk_seen = True
                        prefix = [risk_remainder] if risk_remainder else []
                        prefix_text = risk_remainder
                    elif safety.might_be_risk_directive(prefix_text):
                        continue
                    if risk_seen:
                        # Safety context wins even if a provider ignores the prompt
                        # and tries to add an easter-egg marker after the risk tag.
                        tone, safe_remainder = memes.parse_joke_directive(prefix_text)
                        if tone is not None:
                            prefix_text = safe_remainder
                        elif memes.might_be_joke_directive(prefix_text):
                            continue
                        if not prefix_text:
                            continue
                        awaiting_directive = False
                        token = prefix_text
                    else:
                        tone, remainder = memes.parse_joke_directive(prefix_text)
                        if tone is not None:
                            effect = memes.choose_joke_effect(tone)
                            awaiting_directive = False
                            if remainder and remainder.strip():
                                acc.append(remainder)
                                yield f"data: __joke__:{json.dumps(effect, ensure_ascii=False)}\n\n"
                                effect_sent = True
                                yield f"data: {json.dumps(remainder, ensure_ascii=False)}\n\n"
                            continue
                        if memes.might_be_joke_directive(prefix_text):
                            continue
                        awaiting_directive = False
                        token = prefix_text
                acc.append(token)
                if effect and not effect_sent and token.strip():
                    yield f"data: __joke__:{json.dumps(effect, ensure_ascii=False)}\n\n"
                    effect_sent = True
                yield f"data: {json.dumps(token, ensure_ascii=False)}\n\n"
        except Exception as exc:
            message = "服务出错，请稍后重试"
            if attempt_id:
                api_diagnostics.failure(attempt_id, exc, conv_id=conv_id)
                if use_custom_api:
                    message = api_diagnostics.public_message(exc, attempt_id)
            yield f"data: __error__:{message}\n\n"
            return

        full = "".join(acc).strip()
        if not full:
            empty_reply_error = RuntimeError("Provider returned an empty streamed reply")
            if attempt_id:
                api_diagnostics.failure(attempt_id, empty_reply_error, conv_id=conv_id)
            yield "data: __error__:服务没有返回可显示的回复，请重试。\n\n"
            return

        if attempt_id:
            api_diagnostics.success(attempt_id, conv_id=conv_id)

        user_text, user_image = _content_to_text_and_image(client_messages[0]["content"])
        db.add_message(conv_id, "user", user_text, user_image)
        if effect:
            if effect["kind"] == "six":
                db.add_message(conv_id, "assistant", "6")
            else:
                db.add_message(conv_id, "assistant", memes.meme_message(effect["meme"]))
        if not effect and full.startswith("[JOKE6]"):
            db.add_message(conv_id, "assistant", "6")
            db.add_message(conv_id, "assistant", full.replace("[JOKE6]", "").strip())
        else:
            db.add_message(conv_id, "assistant", full)
        if signal:
            db.record_profile_signal(owner, signal)
        if role == "user" and not use_custom_api:
            db.increment_quota_used(code)
        if notice_to_show:
            db.mark_level_notice_shown(owner)
            yield f"data: __profile_notice__:{json.dumps(notice_to_show, ensure_ascii=False)}\n\n"
        yield "data:__end__\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")

def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def _content_to_text_and_image(content):
    """把用户消息转成纯文本 + 缩略图（若带图片）。返回 (text, image或None)。"""
    if isinstance(content, str):
        return content, None
    if not isinstance(content, list):
        return "", None
    text = ""
    image = None
    for p in content:
        if not isinstance(p, dict):
            continue
        t = p.get("type")
        if t == "text":
            text += p.get("text", "")
        elif t == "image_url":
            iu = p.get("image_url")
            if isinstance(iu, dict):
                image = iu.get("thumbnail") or iu.get("url")
            else:
                image = iu
    return text, image


# ---------- 只读分享页 ----------
@app.get("/share/{token}", response_class=HTMLResponse)
def share_page(token: str):
    f = STATIC_DIR / "share.html"
    return f.read_text(encoding="utf-8") if f.exists() else "share.html not found"


@app.get("/memes/{meme_id}.png", include_in_schema=False)
def meme_asset(meme_id: str):
    filename = memes.MEME_ASSETS.get(meme_id)
    if not filename:
        raise HTTPException(status_code=404, detail="meme not found")
    asset = MEME_DIR / filename
    if not asset.is_file():
        raise HTTPException(status_code=404, detail="meme asset missing")
    return FileResponse(asset, media_type="image/png")

# 前端静态资源（必须放在 API 路由之后挂载）
if MEME_DIR.is_dir():
    app.mount("/memes", StaticFiles(directory=str(MEME_DIR)), name="memes")
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    # 支持宝塔"Python 项目管理器"直接以 main.py 为启动文件运行
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)