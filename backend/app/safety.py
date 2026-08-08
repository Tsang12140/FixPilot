"""Risk-level directives for FixPilot replies.

The model emits a leading marker only; this module turns it into trusted UI data.
"""
import re
from typing import Dict, Optional, Tuple

_RISK_RE = re.compile(r"^\s*\[RISK:(?P<level>medium|high)\]\s*", re.IGNORECASE)

_RISK_NOTICES: Dict[str, Dict[str, str]] = {
    "medium": {
        "level": "medium",
        "title": "?????",
        "message": "????????????????????????????????",
    },
    "high": {
        "level": "high",
        "title": "?????",
        "message": "????????????????????????????????",
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
