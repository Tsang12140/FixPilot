"""Meme easter-egg helpers: the model selects an emotion, the server selects the presentation."""
import random
import re
from typing import Dict, Optional, Tuple


# This is the single filename allowlist. The browser keeps an equivalent allowlist.
MEME_ASSETS = {
    "you_ok": "\u4f60\u6ca1\u4e8b\u5427.png",
    "sick": "\u4f60\u75c5\u5f97\u4e0d\u8f7b.png",
    "head_hold": "\u62b1\u5934\u65e0\u5948.png",
    "face_cover": "\u6342\u8138\u65e0\u5948.png",
    "awkward_laugh": "\u5c2c\u7b11\u65e0\u5948.png",
    "sweat": "\u6d41\u6c57\u65e0\u5948.png",
    "sweat_2": "\u6d41\u6c57\u65e0\u59482.png",
    "cool_gun": "\u51b7\u9177\u6301\u67aa\u6307\u7740\u5bf9\u65b9.png",
    "stop_bothering": "\u80fd\u522b\u6574\u6211\u4e86\u4e0d\uff1f.png",
}

MEME_POOLS = {
    "confused": ("you_ok", "sick"),
    "facepalm": ("head_hold", "face_cover", "awkward_laugh"),
    "sweat": ("sweat", "sweat_2"),
    "cool": ("cool_gun", "stop_bothering"),
}

_JOKE_RE = re.compile(
    r"^\s*(?:\[JOKE:(?P<tone>confused|facepalm|sweat|cool)\]|\[JOKE6\])\s*"
)
_MEME_MESSAGE_RE = re.compile(r"^\[MEME:(?P<meme>[a-z_]+)\]$")


def parse_joke_directive(text: str) -> Tuple[Optional[str], str]:
    """Return the leading model tag and the reply after that tag."""
    match = _JOKE_RE.match(text or "")
    if not match:
        return None, text
    # Keep backward compatibility with the previous prompt marker.
    return match.group("tone") or "legacy_six", text[match.end():]


def might_be_joke_directive(text: str) -> bool:
    """Avoid leaking a partially streamed marker into the visible answer."""
    prefix = (text or "").lstrip()
    if not prefix:
        return True
    return len(prefix) < 64 and ("[JOKE:".startswith(prefix) or prefix.startswith("[JOKE"))


def choose_joke_effect(tone: str) -> Dict[str, str]:
    """Randomly choose 6 or an emotion-matched meme for one confirmed blunder."""
    if tone == "legacy_six":
        return {"kind": "six"}
    if tone not in MEME_POOLS or random.choice(("six", "meme")) == "six":
        return {"kind": "six"}
    return {"kind": "meme", "meme": random.choice(MEME_POOLS[tone])}


def meme_id_from_message(content: str) -> Optional[str]:
    """Read a persisted UI-only marker and return only a safe meme ID."""
    match = _MEME_MESSAGE_RE.fullmatch((content or "").strip())
    if not match:
        return None
    meme_id = match.group("meme")
    return meme_id if meme_id in MEME_ASSETS else None


def meme_message(meme_id: str) -> str:
    if meme_id not in MEME_ASSETS:
        raise ValueError(f"unknown meme: {meme_id}")
    return f"[MEME:{meme_id}]"
