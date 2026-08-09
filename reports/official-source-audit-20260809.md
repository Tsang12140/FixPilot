# Official source registry audit - 2026-08-09

## Scope

Read-only HTTP GET audit of every configured `search_url` in `data/official_sources.json`, following redirects and verifying that the final host is registered for that source. This validates availability and hostname routing, not the correctness of every manual or the content of a page.

## Result after remediation

- 23 enabled runtime sources: 23 reachable with a matching registered host.
- 17 retained candidates: disabled; they cannot unlock automatic lookup.
- 3 nonofficial reference-only entries: all remain disabled.

## Corrections made

- Replaced stale Microsoft recovery, BitLocker, and Windows-update links with currently reachable official Microsoft Learn endpoints.
- Replaced the Intel ARK entry point with its current Intel endpoint and allowed the canonical redirected host.
- Registered Honor's official redirect host and corrected the TP-Link support entry point.
- Disabled and moved back to review: Colorful (was pending yet enabled), Great Wall (404), Acer (timeout), ZOTAC (403), Kingston (403), and Thermaltake (timeout).
- Kept NVIDIA firmware, ONDA, GALAX, Huntkey, and other inaccessible candidates disabled pending a browser/manual review.

## What this does not prove

- A 200 response does not prove that the returned document is the right model or firmware revision.
- A 403/timeout does not prove a domain is fake; it means FixPilot cannot currently treat it as a stable automated source.
- No third-party manual mirror is promoted by this audit.

## Re-run

```powershell
python tools/official_sources_audit.py --enabled-only
```

Only move a candidate back to enabled after its official ownership, current entry point, and intended use have been reviewed. Then run `python tools/official_sources_test.py` before committing.
