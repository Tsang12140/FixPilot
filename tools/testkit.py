"""Shared, project-agnostic plumbing for live API regression suites.

This module deliberately contains no FixPilot diagnosis truth, prompt-injection
payloads, or pass/fail wording. Project suites supply those. Keeping the
transport, authentication, profile setup, image encoding, and SSE parsing here
prevents different suites from silently disagreeing about what an API failure
means.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, Optional, Tuple

import requests


def login_with_code(base: str, code: str) -> str:
    """Log in through an invite code and return the short-lived API token."""
    response = requests.post(
        f"{base.rstrip('/')}/api/auth/invite-login", json={"code": code}, timeout=10
    )
    response.raise_for_status()
    return response.json()["token"]


def login_as_admin(base: str, username: str, password: str) -> str:
    """Log in through the local admin endpoint and return the API token."""
    response = requests.post(
        f"{base.rstrip('/')}/api/auth/admin-login",
        json={"username": username, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["token"]


def create_conversation(base: str, token: str, title: str = "test") -> str:
    """Create an isolated conversation so one test cannot contaminate another."""
    response = requests.post(
        f"{base.rstrip('/')}/api/conversations",
        json={"title": title},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["id"]


def configure_profile(
    base: str,
    token: str,
    technical_level: str,
    response_style: str = "normal",
) -> Dict[str, Any]:
    """Set an explicit profile and verify that the server accepted it.

    Persona tests must test the actual profile passed to FixPilot, not merely a
    tutor that happens to write in a beginner or advanced style.
    """
    response = requests.post(
        f"{base.rstrip('/')}/api/profile/preferences",
        json={
            "technicalLevel": technical_level,
            "responseStyle": response_style,
            "onboardingCompleted": True,
            "onboardingSeen": True,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    profile = response.json().get("profile") or {}
    if profile.get("technical_level") != technical_level:
        raise RuntimeError(
            "Profile setup was not accepted: "
            f"wanted {technical_level!r}, received {profile.get('technical_level')!r}"
        )
    if profile.get("response_style") != response_style:
        raise RuntimeError(
            "Profile setup was not accepted: "
            f"wanted {response_style!r}, received {profile.get('response_style')!r}"
        )
    return profile


def _image_content(text: str, image_path: str, assets_dir: Optional[str]) -> Tuple[Any, Optional[str]]:
    """Build the same image payload shape as the browser client."""
    full_path = image_path
    if not os.path.isabs(full_path) and assets_dir:
        full_path = os.path.join(assets_dir, image_path)
    if not os.path.isfile(full_path):
        return f"{text}  [image file missing: {image_path}]", image_path

    with open(full_path, "rb") as image_file:
        image_b64 = base64.b64encode(image_file.read()).decode("ascii")
    ext = os.path.splitext(full_path)[1].lower()
    mime = {".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    data_url = f"data:{mime};base64,{image_b64}"
    return [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": data_url, "thumbnail": data_url}},
    ], None


def send_chat(
    base: str,
    token: str,
    text: str,
    conv_id: Optional[str] = None,
    image_path: Optional[str] = None,
    assets_dir: Optional[str] = None,
    timeout: int = 120,
) -> Tuple[str, int, Dict[str, Any]]:
    """Send one chat turn and normalize its SSE outcome.

    The numeric status is the actual HTTP status. A server-side SSE error is
    deliberately represented as HTTP 200 plus ``stream_error=True``; treating
    it as a fake HTTP 500 was the source of an earlier bad diagnosis.
    """
    content: Any = text
    image_missing: Optional[str] = None
    if image_path:
        content, image_missing = _image_content(text, image_path, assets_dir)

    body: Dict[str, Any] = {"messages": [{"role": "user", "content": content}]}
    if conv_id:
        body["convId"] = conv_id
    headers = {"Authorization": f"Bearer {token}"}
    base = base.rstrip("/")

    try:
        response = requests.post(
            f"{base}/api/chat", json=body, headers=headers, stream=True, timeout=timeout
        )
    except requests.RequestException as exc:
        return "", 0, {
            "error": f"request_exception: {exc}",
            "request_error": True,
            "risk": False,
            "joke": False,
            "options": [],
            "image_missing": image_missing,
        }

    if response.status_code != 200:
        try:
            detail = response.text[:500]
        except requests.RequestException:
            detail = ""
        return "", response.status_code, {
            "error": detail,
            "risk": False,
            "joke": False,
            "options": [],
            "image_missing": image_missing,
        }

    full_reply = ""
    risk_notice: Optional[Dict[str, Any]] = None
    joke = False
    profile_notice = ""
    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "__start__":
                continue
            if data == "__end__":
                break
            if data.startswith("__error__:"):
                return "", 200, {
                    "error": data[len("__error__:"):],
                    "stream_error": True,
                    "risk": False,
                    "joke": False,
                    "options": [],
                    "image_missing": image_missing,
                }
            if data.startswith("__risk__:"):
                raw_notice = data[len("__risk__:"):]
                try:
                    risk_notice = json.loads(raw_notice)
                except json.JSONDecodeError:
                    risk_notice = {"raw": raw_notice}
                continue
            if data.startswith("__joke__:"):
                joke = True
                continue
            if data.startswith("__profile_notice__:"):
                profile_notice = data[len("__profile_notice__:"):]
                continue
            try:
                full_reply += json.loads(data)
            except (json.JSONDecodeError, TypeError):
                full_reply += data
    except requests.RequestException as exc:
        return "", 200, {
            "error": f"stream_exception: {exc}",
            "stream_error": True,
            "risk": False,
            "joke": False,
            "options": [],
            "image_missing": image_missing,
        }

    return full_reply, 200, {
        "risk": risk_notice is not None,
        "risk_notice": risk_notice,
        "joke": joke,
        "options": parse_numbered_options(full_reply),
        "profile_notice": profile_notice,
        "image_missing": image_missing,
    }


def parse_numbered_options(reply: str) -> list[str]:
    """Extract the legacy plain-text option format for test observations only."""
    if "\u9009\u9879\uff1a" not in reply and "\u9009\u9879:" not in reply:
        return []
    import re

    match = re.search("\u9009\u9879[\uff1a:]\\s*([\\s\\S]+)", reply)
    if not match:
        return []
    return [item.strip() for item in re.split(r"\n?\d+[.?)]\s*", match.group(1)) if item.strip()]


def transport_issue(status: int, extra: Dict[str, Any], reply: str) -> Optional[str]:
    """Return a normalized infrastructure issue; never turn it into a PASS."""
    if extra.get("request_error"):
        return "request_error"
    if status != 200:
        return "http_error"
    if extra.get("stream_error"):
        return "stream_error"
    if not reply or not reply.strip():
        return "empty_reply"
    return None
