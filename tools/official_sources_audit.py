"""Live, read-only audit of FixPilot's official-reference registry.

This is deliberately separate from the no-network regression suite. A 403 or
network error means "review needed", not automatically "not official".
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "official_sources.json"


def host_matches(host: str, domains) -> bool:
    normalized = (host or "").lower().rstrip(".")
    return any(
        normalized == str(domain).lower().rstrip(".")
        or normalized.endswith("." + str(domain).lower().rstrip("."))
        for domain in (domains or [])
    )


async def check_entry(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, entry: dict) -> dict:
    url = entry.get("search_url")
    async with semaphore:
        try:
            response = await client.get(url)
            final_url = str(response.url)
            final_host = urlparse(final_url).hostname or ""
            host_ok = host_matches(final_host, entry.get("domains"))
            status = response.status_code
            return {
                "id": entry["id"],
                "enabled": bool(entry.get("enabled")),
                "review_status": entry.get("review_status"),
                "input_url": url,
                "final_url": final_url,
                "http_status": status,
                "host_matches_registry": host_ok,
                "result": "reachable" if 200 <= status < 400 and host_ok else "review_needed",
                "detail": "",
            }
        except httpx.HTTPError as exc:
            return {
                "id": entry["id"],
                "enabled": bool(entry.get("enabled")),
                "review_status": entry.get("review_status"),
                "input_url": url,
                "final_url": "",
                "http_status": None,
                "host_matches_registry": False,
                "result": "review_needed",
                "detail": type(exc).__name__,
            }


async def run_live_audit(include_disabled: bool) -> dict:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = []
    for group in ("official_sources", "citation_only_sources"):
        for item in registry.get(group, []):
            if item.get("search_url") and (include_disabled or item.get("enabled")):
                entries.append(item)
    timeout = httpx.Timeout(18.0, connect=10.0)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FixPilotSourceAudit/1.0)"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
        semaphore = asyncio.Semaphore(5)
        results = await asyncio.gather(*(check_entry(client, semaphore, entry) for entry in entries))
    return {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "registry_path": str(REGISTRY_PATH.relative_to(ROOT)),
        "include_disabled": include_disabled,
        "summary": {
            "total": len(results),
            "reachable": sum(item["result"] == "reachable" for item in results),
            "review_needed": sum(item["result"] == "review_needed" for item in results),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only official-source registry URL audit")
    parser.add_argument("--enabled-only", action="store_true", help="skip disabled candidates and reference-only entries")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    audit = asyncio.run(run_live_audit(include_disabled=not args.enabled_only))
    if args.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        summary = audit["summary"]
        print(f"Official-source audit: {summary['reachable']} reachable / {summary['review_needed']} review / {summary['total']} total")
        for result in audit["results"]:
            if result["result"] != "reachable":
                print(f"- {result['id']}: HTTP {result['http_status'] or result['detail']} | host_match={result['host_matches_registry']}")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
