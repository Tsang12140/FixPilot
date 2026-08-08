"""Risk-level directives for FixPilot replies.

The model emits a leading marker only; this module turns it into trusted UI data.
"""
import re
from typing import Dict, Optional, Tuple

_RISK_RE = re.compile(r"^\s*\[RISK:(?P<level>medium|high)\]\s*", re.IGNORECASE)

_RISK_NOTICES: Dict[str, Dict[str, str]] = {
    "medium": {
        "level": "medium",
        "title": "中风险操作",
        "message": "这一步会改动系统、驱动或设备状态。先看清对象和恢复方式，再继续。",
    },
    "high": {
        "level": "high",
        "title": "高风险操作",
        "message": "这一步可能影响数据、启动或硬件。先备份并确认目标；不确定就停止。",
    },
}


def parse_risk_directive(text: str) -> Tuple[Optional[str], str]:
    """Return a recognized leading level and the answer without the marker."""
    match = _RISK_RE.match(text or "")
    if not match:
        return None, text
    return match.group("level").lower(), text[match.end():]


def might_be_risk_directive(text: str) -> bool:
    """Hold back a partially streamed marker so it never reaches the user."""
    prefix = (text or "").lstrip()
    if not prefix:
        return True
    candidates = ("[RISK:MEDIUM]", "[RISK:HIGH]")
    return len(prefix) < 20 and any(candidate.startswith(prefix.upper()) for candidate in candidates)


def risk_notice(level: str) -> Dict[str, str]:
    return dict(_RISK_NOTICES[level])
