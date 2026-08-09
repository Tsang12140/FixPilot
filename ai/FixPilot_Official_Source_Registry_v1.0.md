# FixPilot Official Source Registry v1.0

Status: implemented as a conservative runtime gate on 2026-08-09.

## Purpose

`data/official_sources.json` is a routing catalogue, not a replacement for FixPilot's local fault-diagnosis knowledge base and not a mirrored manual library. It answers only: when an official reference is genuinely necessary, which manufacturer-owned support domains may be considered for this turn?

## Runtime contract

1. Local retrieval, current evidence, diagnostic state, and safety policy always come first.
2. The browser exposes no search control. Only the server can make the optional official-reference tool available.
3. Tool availability requires all of the following:
   - official DeepSeek V4 Flash provider gate;
   - a registry record with `enabled=true`, `review_status=???`, `officiality=??`, and `source_tier=official_verified`;
   - a vendor match and the record's required identifier in the current conversation (normally an exact product model).
4. The model may still decide that no lookup is needed. It must not browse merely to make a normal diagnosis look comprehensive.
5. A returned provider URL is displayed as a source only when its hostname equals, or is a subdomain of, a selected registry domain. Lookalikes such as `asus.com.example.test` are rejected.
6. If a provider lookup does not return an allowed official URL, FixPilot does not present that external conclusion as diagnostic evidence. It asks for the exact model or official support link and continues the local diagnostic chain.

## Source states

- `official_verified`: eligible for runtime routing.
- `official_candidate`: retained for review but never routed automatically.
- `nonofficial_reference_only`: manual mirrors and archives. They remain disabled and cannot become an official source automatically.

`enabled` is an execution switch, not a claim that a vendor exists. A real but unreachable, redirected, expired, or bot-blocked page can remain a candidate until a human review restores it.

## High-risk material

Records marked `risk_level=high` require a target confirmation. Hardware/firmware records also require an exact model. Registry approval never bypasses the existing R1/R2/R3 safety policies, data-backup confirmation, or stop-guidance rules.

## Maintenance

No-network integrity test:

```powershell
python tools/official_sources_test.py
```

Live read-only URL audit:

```powershell
python tools/official_sources_audit.py
python tools/official_sources_audit.py --enabled-only
```

A URL audit confirms reachability and registered-host matching only. It does not prove document accuracy, current firmware applicability, or license permission to mirror content. Do not ingest or redistribute manuals merely because their links are listed.

## Known provider limitation

The currently supported DeepSeek web-search tool does not provide a documented server-side domain-filter parameter in this integration. FixPilot therefore applies three layers: no tool unless a source route is selected, an explicit per-turn approved-domain policy, and final URL allowlist filtering. This is a conservative v1 boundary; a future direct manufacturer-fetcher can provide stronger transport-level domain control.
