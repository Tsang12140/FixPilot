"""Runtime gate for FixPilot's curated official-reference registry.

The registry does not replace retrieval.  It merely narrows when the optional
external-reference tool can be exposed, and which manufacturer domains may be
shown back to a user as evidence.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Set
from urllib.parse import urlparse


REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "official_sources.json"
OFFICIALITY = "\u5b98\u65b9"
VERIFIED = "\u5df2\u9a8c\u8bc1"

# A deliberately conservative signal: a vendor name alone is not enough to
# search externally.  The user must have supplied an identifiable product.
_MODEL_TOKEN = re.compile(
    r"\b(?:[a-z]{1,12}[-_ ]?\d{2,5}[a-z0-9_-]*|(?:rtx|gtx|rx|arc)\s*\d{3,4}[a-z0-9_-]*|(?:thinkpad|matebook|redmibook)\s*[a-z]?\d[\w-]*)\b",
    re.IGNORECASE,
)
_OS_VERSION = re.compile(r"\b(?:windows|win)\s*(?:10|11|server\s*20\d{2})\b", re.IGNORECASE)
_KB_OR_ERROR = re.compile(r"\b(?:kb\d{5,}|0x[0-9a-f]{6,})\b", re.IGNORECASE)
_COMMAND = re.compile(r"\b(?:diskpart|sfc|dism|bcdboot|chkdsk|bcdedit)\b", re.IGNORECASE)
_FEATURES = ("bitlocker", "\u8bbe\u5907\u52a0\u5bc6", "winre", "\u6062\u590d\u73af\u5883")


@lru_cache(maxsize=1)
def load_registry() -> Dict:
    """Read the curated registry.  Invalid JSON disables lookup rather than
    degrading into a general web search."""
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"official_sources": [], "_meta": {"vendor_aliases": {}}}
    if not isinstance(data, dict) or not isinstance(data.get("official_sources"), list):
        return {"official_sources": [], "_meta": {"vendor_aliases": {}}}
    return data


def clear_registry_cache() -> None:
    """Useful for tests and local development after changing the JSON file."""
    load_registry.cache_clear()


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _has_product_model(query: str) -> bool:
    for match in _MODEL_TOKEN.finditer(query):
        token = match.group(0).replace(" ", "").casefold()
        if token not in {"windows10", "windows11", "win10", "win11"}:
            return True
    return False


def _has_identifier(query: str, identifier: str) -> bool:
    if identifier == "model":
        return _has_product_model(query)
    if identifier == "os_version":
        return bool(_OS_VERSION.search(query))
    if identifier == "kb_or_error_code":
        return bool(_KB_OR_ERROR.search(query))
    if identifier == "command":
        return bool(_COMMAND.search(query))
    if identifier in {"feature", "error_code_or_feature"}:
        has_feature = any(term in query for term in _FEATURES)
        return has_feature or bool(_KB_OR_ERROR.search(query))
    return False


def is_enabled_verified_official(source: Dict) -> bool:
    return bool(
        source.get("enabled")
        and source.get("officiality") == OFFICIALITY
        and source.get("review_status") == VERIFIED
        and source.get("source_tier") == "official_verified"
        and source.get("lookup_mode") == "official_site_only"
        and source.get("search_url")
    )


def select_official_sources(query: str, limit: int = 3) -> List[Dict]:
    """Return a small set of registry-approved references for this exact turn.

    Selection is intentionally conservative: unknown brand/model means no
    external tool, so the normal knowledge-base diagnosis continues instead.
    """
    normalized = _normalize_text(query)
    if not normalized:
        return []
    registry = load_registry()
    aliases = registry.get("_meta", {}).get("vendor_aliases", {})
    selected: List[Dict] = []
    for source in registry.get("official_sources", []):
        if not isinstance(source, dict) or not is_enabled_verified_official(source):
            continue
        vendor_terms = [source.get("vendor", "")] + list(aliases.get(source.get("vendor"), []))
        if not any(_normalize_text(term) and _normalize_text(term) in normalized for term in vendor_terms):
            continue
        requirements = source.get("required_identifiers") or ["model"]
        if not all(_has_identifier(normalized, str(requirement)) for requirement in requirements):
            continue
        selected.append(source)
        if len(selected) >= limit:
            break
    return selected


def allowed_domains(sources: Iterable[Dict]) -> Set[str]:
    domains: Set[str] = set()
    for source in sources:
        for domain in source.get("domains") or []:
            normalized = str(domain).strip().lower().rstrip(".")
            if normalized and "://" not in normalized and "/" not in normalized:
                domains.add(normalized)
    return domains


def is_allowed_url(url: str, domains: Iterable[str]) -> bool:
    try:
        parsed = urlparse(str(url).strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def build_lookup_policy(sources: Iterable[Dict]) -> str:
    """Give the model only the few official sites allowed for this turn."""
    items = list(sources)
    if not items:
        return ""
    entries = "\\n".join(
        f"- {item['name']} | domains: {', '.join(item['domains'])} | entry: {item['search_url']} | purpose: {', '.join(item.get('allowed_purposes') or ['manual'])}"
        for item in items
    )
    return """[Registry-constrained official lookup]
External lookup is available only because this turn supplied a matching vendor and identifiable product/identifier. It remains optional: local knowledge base and the current diagnostic chain come first.
If, and only if, an official reference is necessary for the next diagnostic step, search within the approved domains below. Use a site-restricted query and cite only results from those domains. Never use a forum, mirror, snippet, or another domain as evidence. If no approved official result is returned, say that the official reference could not be verified and continue normal diagnosis; do not replace it with a generic web answer.
Approved sources for this turn:
""" + entries
