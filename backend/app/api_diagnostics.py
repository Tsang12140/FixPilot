"""Sanitized diagnostics for user-supplied OpenAI-compatible APIs."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict
from uuid import uuid4

import httpx

from . import config

LOG_PATH = config.ROOT_DIR / "backend" / "logs" / "api-diagnostics.log"
_SECRET_PATTERN = re.compile(r"(?i)\b(?:ark|sk)-[A-Za-z0-9_\-]{4,}\b")
_BEARER_PATTERN = re.compile(r"(?i)(Bearer\s+)[^\s,;\"']+")


def redact(value: Any, limit: int = 1200) -> str:
    """Keep provider diagnostics useful without ever persisting an API key."""
    text = str(value or "")
    text = _SECRET_PATTERN.sub("[REDACTED_API_KEY]", text)
    text = _BEARER_PATTERN.sub(r"\1[REDACTED_API_KEY]", text)
    return text[:limit]


def _write(entry: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def key_metadata(api_key: str) -> Dict[str, Any]:
    """Diagnostic-only key facts; the secret value is never written to disk."""
    raw = str(api_key or "")
    trimmed = raw.strip()
    return {
        "api_key": "[NOT_LOGGED]",
        "api_key_present": bool(trimmed),
        "api_key_length": len(trimmed),
        "api_key_prefix": trimmed[:4] if trimmed else "",
        "api_key_last4": trimmed[-4:] if trimmed else "",
        "api_key_has_bearer_prefix": trimmed.lower().startswith("bearer "),
        "api_key_fingerprint": hashlib.sha256(trimmed.encode("utf-8")).hexdigest()[:12] if trimmed else "",
    }


def start(kind: str, api_base: str, model: str, api_key: str = "", conv_id: str = "") -> str:
    event_id = f"api-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
    entry = {
        "id": event_id,
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": "start",
        "kind": kind,
        "api_base": redact(api_base),
        "model": redact(model),
    }
    if conv_id:
        entry["conv_id"] = conv_id
    entry.update(key_metadata(api_key))
    _write(entry)
    return event_id


def success(event_id: str, conv_id: str = "") -> None:
    entry = {
        "id": event_id,
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": "success",
    }
    if conv_id:
        entry["conv_id"] = conv_id
    _write(entry)


def upstream_detail(exc: Exception) -> tuple[int | None, str]:
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        try:
            body = response.json()
            if isinstance(body, dict):
                error = body.get("error", body)
                if isinstance(error, dict):
                    message = error.get("message") or error.get("msg") or json.dumps(error, ensure_ascii=False)
                else:
                    message = json.dumps(body, ensure_ascii=False)
            else:
                message = json.dumps(body, ensure_ascii=False)
        except Exception:
            message = response.text
        return response.status_code, redact(message)
    return None, redact(exc)


def failure(event_id: str, exc: Exception, conv_id: str = "") -> tuple[int | None, str]:
    status, detail = upstream_detail(exc)
    entry = {
        "id": event_id,
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": "failure",
        "http_status": status,
        "provider_detail": detail,
        "exception": type(exc).__name__,
    }
    if conv_id:
        entry["conv_id"] = conv_id
    _write(entry)
    return status, detail


def public_message(exc: Exception, event_id: str) -> str:
    status, detail = upstream_detail(exc)
    lowered = detail.lower()
    quota_terms = ("insufficient", "balance", "quota", "billing", "credit", "\u4f59\u989d", "\u989d\u5ea6", "\u914d\u989d")
    if any(term in lowered for term in quota_terms):
        base = "\u4f60\u7684\u81ea\u5b9a\u4e49 API \u6ca1\u6709\u53ef\u7528\u989d\u5ea6\u6216\u914d\u989d\uff0cFixPilot \u9080\u8bf7\u7801\u6b21\u6570\u6ca1\u6709\u6263\u9664\u3002\u8bf7\u5728\u670d\u52a1\u5546\u63a7\u5236\u53f0\u68c0\u67e5\u989d\u5ea6\uff0c\u6216\u6e05\u9664\u81ea\u5b9a\u4e49 API \u540e\u4f7f\u7528\u9ed8\u8ba4 API\u3002"
    elif status == 401:
        base = "API Key \u65e0\u6548\u3001\u5df2\u8fc7\u671f\u6216\u4e0e\u5f53\u524d\u670d\u52a1\u5546\u4e0d\u5339\u914d\u3002"
    elif status == 403:
        base = "API Key \u6ca1\u6709\u8bbf\u95ee\u8fd9\u4e2a\u6a21\u578b\u7684\u6743\u9650\u3002"
    elif status == 404:
        base = "API \u5730\u5740\u6216\u6a21\u578b\u540d\u4e0d\u5b58\u5728\u3002"
    elif status == 429:
        base = "\u81ea\u5b9a\u4e49 API \u88ab\u670d\u52a1\u5546\u9650\u901f\u6216\u914d\u989d\u9650\u5236\uff0cFixPilot \u9080\u8bf7\u7801\u6b21\u6570\u6ca1\u6709\u6263\u9664\u3002\u8bf7\u7a0d\u540e\u518d\u8bd5\uff1b\u5982\u679c\u6301\u7eed\u51fa\u73b0\uff0c\u8bf7\u68c0\u67e5\u670d\u52a1\u5546\u7684\u989d\u5ea6\u3002"
    elif isinstance(exc, httpx.ConnectError):
        base = "\u65e0\u6cd5\u8fde\u63a5 API \u5730\u5740\uff0c\u8bf7\u68c0\u67e5\u5730\u5740\u548c\u7f51\u7edc\u3002"
    elif isinstance(exc, httpx.TimeoutException):
        base = "API \u54cd\u5e94\u8d85\u65f6\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002"
    else:
        base = f"\u81ea\u5b9a\u4e49 API \u8c03\u7528\u5931\u8d25{f' (HTTP {status})' if status else ''}\u3002"
    return f"{base} \u8bca\u65ad\u7f16\u53f7\uff1a{event_id}\u3002"
