"""UI-only reaction helpers for the roast-mode easter eggs.

The model may request an emotion. This module alone decides whether that
request is allowed and which small visual effect is persisted. Keeping that
decision out of the model prevents repeated ``6`` messages and lets old
transcripts remain readable.
"""
import random
import re
from typing import Dict, Iterable, Optional, Tuple


# This is the single filename allowlist. The browser keeps an equivalent list.
# ``sick`` intentionally is not an active asset: it reads as attacking the user.
MEME_ASSETS = {
    "you_ok": "\u4f60\u6ca1\u4e8b\u5427.png",
    "head_hold": "\u62b1\u5934\u65e0\u5948.png",
    "face_cover": "\u6342\u8138\u65e0\u5948.png",
    "awkward_laugh": "\u5c2c\u7b11\u65e0\u5948.png",
    "sweat": "\u6d41\u6c57\u65e0\u5948.png",
    "sweat_2": "\u6d41\u6c57\u65e0\u59482.png",
    "cool_gun": "\u51b7\u9177\u6301\u67aa\u6307\u7740\u5bf9\u65b9.png",
    "stop_bothering": "\u80fd\u522b\u6574\u6211\u4e86\u4e0d\uff1f.png",
}

MEME_POOLS = {
    "confused": ("you_ok",),
    "facepalm": ("head_hold", "face_cover", "awkward_laugh"),
    "sweat": ("sweat", "sweat_2"),
    "cool": ("cool_gun", "stop_bothering"),
}
REACTION_LABELS = {"six": "6", "chichi": "\u5f73\u4e8d\u3002"}

_JOKE_RE = re.compile(
    r"^\s*(?:\[JOKE:(?P<tone>confused|facepalm|sweat|cool|chichi)\]|\[JOKE6\])\s*"
)
_MEME_MESSAGE_RE = re.compile(r"^\[MEME:(?P<meme>[a-z_]+)\]$")
_REACTION_MESSAGE_RE = re.compile(r"^\[REACTION:(?P<reaction>six|chichi)\]$")
_ACKNOWLEDGEMENT_RE = re.compile(
    r"^\s*(?:\u8c22\u8c22|\u591a\u8c22|\u611f\u8c22|\u8c22\u4e86|"
    r"\u660e\u767d\u4e86|\u61c2\u4e86|\u597d\u7684|\u6536\u5230|"
    r"ok|okay|thanks|thx|\u54c8+|\u7b11\u6b7b\u4e86|"
    r"\u767d\u6298\u817e\u4e86|\u539f\u6765\u5982\u6b64)"
    r"[\s\u3002\uff01!~\uff5e\u3001,\uff0c]*$",
    re.IGNORECASE,
)


def parse_joke_directive(text: str) -> Tuple[Optional[str], str]:
    """Return the leading model tag and the reply after that tag."""
    match = _JOKE_RE.match(text or "")
    if not match:
        return None, text
    # Keep old model output readable, but new prompts must use [JOKE:<tone>].
    return match.group("tone") or "legacy_six", text[match.end():]


def might_be_joke_directive(text: str) -> bool:
    """Avoid leaking a partially streamed marker into the visible answer."""
    prefix = (text or "").lstrip()
    if not prefix:
        return True
    return len(prefix) < 64 and ("[JOKE:".startswith(prefix) or prefix.startswith("[JOKE"))


def meme_id_from_message(content: str) -> Optional[str]:
    """Read a persisted UI-only marker and return only a safe meme ID."""
    match = _MEME_MESSAGE_RE.fullmatch((content or "").strip())
    if not match:
        return None
    meme_id = match.group("meme")
    return meme_id if meme_id in MEME_ASSETS else None


def reaction_id_from_message(content: str) -> Optional[str]:
    """Read a semantic reaction marker, including the legacy raw ``6``."""
    normalized = (content or "").strip()
    if normalized == "6":
        return "six"
    match = _REACTION_MESSAGE_RE.fullmatch(normalized)
    return match.group("reaction") if match else None


def is_ui_effect_message(content: str) -> bool:
    """Whether a persisted assistant row is presentation-only, not context."""
    return bool(meme_id_from_message(content) or reaction_id_from_message(content))


def meme_message(meme_id: str) -> str:
    if meme_id not in MEME_ASSETS:
        raise ValueError(f"unknown meme: {meme_id}")
    return f"[MEME:{meme_id}]"


def reaction_message(reaction_id: str) -> str:
    if reaction_id not in REACTION_LABELS:
        raise ValueError(f"unknown reaction: {reaction_id}")
    return f"[REACTION:{reaction_id}]"


def _message_value(message, name: str, default=""):
    return message.get(name, default) if isinstance(message, dict) else getattr(message, name, default)


def _effect_history(messages: Iterable[dict]):
    effects = []
    for message in messages:
        if _message_value(message, "role") != "assistant":
            continue
        content = _message_value(message, "content", "")
        reaction_id = reaction_id_from_message(content)
        meme_id = meme_id_from_message(content)
        if reaction_id:
            effects.append(("reaction", reaction_id))
        elif meme_id:
            effects.append(("meme", meme_id))
    return effects


def is_acknowledgement(text: str) -> bool:
    """Acknowledge/review messages never deserve an extra visual reaction."""
    return bool(_ACKNOWLEDGEMENT_RE.fullmatch((text or "").strip()))


def can_emit_reaction(history: Iterable[dict], current_user_text: str) -> bool:
    """Enforce acknowledgement and three-assistant-message reaction cooldown."""
    if is_acknowledgement(current_user_text):
        return False
    assistant_messages_since_effect = 0
    for message in reversed(list(history)):
        content = _message_value(message, "content", "")
        if _message_value(message, "role") == "assistant" and is_ui_effect_message(content):
            return assistant_messages_since_effect >= 3
        if _message_value(message, "role") == "assistant" and str(content).strip():
            assistant_messages_since_effect += 1
    return True


def choose_joke_effect(
    tone: str,
    history: Iterable[dict] = (),
    *,
    allowed: bool = True,
    random_value=None,
) -> Optional[Dict[str, str]]:
    """Choose one restrained effect; return None when the request is ineligible.

    The first eligible non-legacy marker can become ``6`` at low probability.
    Once ``6`` exists in a conversation it is never repeated; later eligible
    markers prefer their matching meme. ``chichi`` is a separate compact card.
    """
    history = list(history)
    prior_effects = _effect_history(history)
    if not allowed or not can_emit_reaction(history, ""):
        return None
    if tone == "chichi":
        return {"kind": "reaction", "reaction": "chichi"}
    if tone == "legacy_six":
        if any(kind == "reaction" and effect == "six" for kind, effect in prior_effects):
            return None
        return {"kind": "reaction", "reaction": "six"}
    if tone not in MEME_POOLS:
        return None

    roll = random_value if random_value is not None else random.random()
    already_six = any(kind == "reaction" and effect == "six" for kind, effect in prior_effects)
    if not already_six and roll < 0.30:
        return {"kind": "reaction", "reaction": "six"}
    if roll > 0.90:
        return None

    # Do not immediately reuse the same meme where the tone has alternatives.
    previous_meme = next((effect for kind, effect in reversed(prior_effects) if kind == "meme"), None)
    choices = tuple(item for item in MEME_POOLS[tone] if item != previous_meme) or MEME_POOLS[tone]
    return {"kind": "meme", "meme": random.choice(choices)}
