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


def infer_risk_level(text: str) -> Optional[str]:
    """Return a conservative risk tier for a user-requested operation.

    Model markers remain the preferred signal. This fallback protects users when
    a direct request clearly names a risky operation but the model forgets its
    presentation marker. It deliberately requires both a subject and an action
    for BIOS/driver cases, so a harmless explanatory question is not promoted.
    """
    normalized = (text or "").lower()
    bios_subject = "bios" in normalized or "uefi" in normalized
    bios_actions = (
        "enter", "change", "set", "save", "flash", "update", "overclock",
        "xmp", "expo", "\u8fdb\u5165", "\u4fee\u6539", "\u6539", "\u8bbe\u7f6e",
        "\u4fdd\u5b58", "\u5237\u5199", "\u66f4\u65b0", "\u8d85\u9891", "\u542f\u52a8\u987a\u5e8f",
        "\u5185\u5b58", "\u65f6\u5e8f", "\u7535\u538b",
    )
    if bios_subject and any(action in normalized for action in bios_actions):
        return "high"

    high_terms = (
        "format", "partition", "bitlocker", "tpm", "firmware", "\u683c\u5f0f\u5316",
        "\u5206\u533a", "\u56fa\u4ef6", "\u77ed\u63a5\u7535\u6e90", "\u56de\u5f62\u9488",
    )
    if any(term in normalized for term in high_terms):
        return "high"

    driver_subject = "driver" in normalized or "ddu" in normalized or "\u9a71\u52a8" in normalized
    driver_actions = (
        "uninstall", "reinstall", "rollback", "remove", "clean", "\u5378\u8f7d",
        "\u91cd\u88c5", "\u518d\u88c5", "\u5378\u6389", "\u56de\u9000", "\u5220\u9664", "\u6e05\u7406",
    )
    if driver_subject and any(action in normalized for action in driver_actions):
        return "medium"
    return None

def risk_notice(level: str) -> Dict[str, str]:
    return dict(_RISK_NOTICES[level])
