# FixPilot Official Source Registry v1.0

Status: implemented as a conservative runtime gate on 2026-08-09.

## Purpose

`data/official_sources.json` is a preferred-source routing catalogue, not a replacement for FixPilot's local fault-diagnosis knowledge base and not a mirrored manual library. It answers: when an external official reference is genuinely necessary, which curated manufacturer-owned support domains should FixPilot try first for this turn? It is not an internet wall.

## Runtime contract

1. Local knowledge base, diagnostic chain, and safety policy remain the default. Ordinary symptom chats never gain search merely because a provider supports it.
2. The browser exposes no search control. Only the server can make the optional official-reference tool available.
3. Tool availability requires the official DeepSeek V4 Flash provider gate and either:
   - an enabled, verified, official registry record with a vendor and required identifier match; or
   - a concrete, identifiable product-document request (for example a model plus manual, driver, firmware, BIOS/UEFI, specification, or compatibility request) when the vendor is not yet in the registry.
4. Registry matches are preferred starting points, not an exhaustive allowlist. The model may broaden only when the preferred sources lack the necessary material, and then only to a direct manufacturer, operating-system, or hardware-vendor official page.
5. The model may still decide that no lookup is needed. It must not browse merely to make a normal diagnosis look comprehensive.
6. Returned sources are disclosed transparently:
   - hostname equals, or is a subdomain of, a selected registry domain: label it `优先官方来源`;
   - any other returned HTTP(S) page: label it `外部线索（未列入优先目录）` and state that important actions need an official-source cross-check.
7. Forums, mirrors, snippets, and unverified third-party pages are never a confirmed basis for firmware, BIOS, data, partition, or hardware-risk actions. An unlisted result is a lead until source ownership and exact-model applicability are verified.


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

The currently supported DeepSeek web-search tool does not provide a documented server-side domain-preference parameter in this integration. FixPilot therefore applies three layers: no tool for ordinary symptoms, an explicit per-turn preferred-domain policy, and transparent source labels after retrieval. This preserves a fast, trusted first route without pretending that the catalogue covers every manufacturer. A future direct manufacturer-fetcher can provide stronger transport-level source control.
