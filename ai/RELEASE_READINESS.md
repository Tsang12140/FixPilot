# FixPilot release-readiness gate

> Audit date: 2026-08-09 (Asia/Shanghai)
>
> Scope: current codebase and recorded verification evidence. This is an engineering release gate, not a claim that every planned AI-policy document is already implemented.

## Decision

**Do not open unrestricted public registration yet.**

The app is suitable for a small, informed invite-only beta once the P0 checks below are completed with the actual production model/configuration. A reasonable first batch is 3-10 known testers using non-critical machines and non-sensitive screenshots.

The distinction matters: the product has a strong UI and diagnostic foundation, but a computer-repair assistant must be reliable under streaming failure, provider quota failure, safety-sensitive prompts, and privacy expectations before it is presented as a broadly usable service.

## What is already in place

- One-question-at-a-time diagnostic interaction, RAG, OCR for screenshot text, history, image upload, invitation/account flow, model picker, share pages, and risk-warning treatment exist in the product.
- Interrupted/blank streams have a recovery path rather than leaving an empty chat gap.
- Targeted runtime checks previously confirmed a real OCR image path and two multi-turn conversations without stream/HTTP/empty-reply errors; static checks pass for the modular test harness.
- Regression tooling now separates injection, safety, and dynamic persona diagnosis and produces PASS / FAIL / ERROR / REVIEW rather than hiding provider errors as test passes.

## P0 - required before invite-only beta

1. **Run a live regression baseline on the intended model.**
   - Run the 12 injection cases, S01-S04 safety cases, and all 9 A/B/C diagnostic scenarios against the exact model/provider to be offered.
   - Treat any `ERROR`, `FAIL`, or `REVIEW` as a release decision, not as a cosmetic warning.
   - The stricter grader currently exposes an unresolved content-quality concern in the former I03 / current B03 branch: the model can choose the wrong diagnosis direction even when transport succeeds.

2. **Test failure handling with the real provider.**
   - Save and test the active API configuration.
   - Verify a normal multi-turn stream, an upstream 4xx/5xx, a stream ending without displayable content, and an exhausted quota/balance response.
   - The user must receive a clear retry/configuration message; failed replies must not consume a quota turn. Keep the redacted diagnostic ID for support.

3. **Make the database/deployment baseline intentional.**
   - Resolve and review the current uncommitted SQLite/WAL changes before deployment.
   - Take a backup, restore it into a clean local copy, and prove conversations/accounts still open.
   - Define a production start/restart procedure and a health check.

4. **Tell beta testers how their data is handled.**
   - Administrators can inspect users' conversation records. Before inviting anyone, disclose that clearly and provide a basic retention/deletion contact path.
   - Ask testers not to send passwords, license keys, private documents, or screenshots containing secrets.

5. **Final UI smoke test after all code is merged.**
   - Desktop plus 390px and 320px mobile.
   - Check model menu, focused mobile keyboard state, settings default Account tab, conversation refresh/deep link, image sending, safety warning card, failed-reply recovery, and no horizontal overflow.

## P1 - required before a public launch

- Production HTTPS/domain, process supervision, error-log rotation, alerting, and tested backup/restore.
- Per-user rate limiting and explicit image/message size limits.
- A concise privacy policy, retention/deletion policy, support contact, and a visible statement that FixPilot can be wrong and important information needs verification.
- An operations checklist for provider outage, quota exhaustion, unsafe advice reports, and account abuse.
- Browser regression automation for the responsive UI hotspots rather than relying only on manual screenshots.
- Repeat the full live regression whenever the system prompt, safety policy, RAG corpus, model adapter, or model identifier changes.

## Current internal cohort terminology

For tests and reports only:

| Internal cohort | Runtime stored value | User-facing choice |
| --- | --- | --- |
| A | `advanced` | not shown to users |
| B | `intermediate` | not shown to users |
| C | `beginner` | not shown to users |

A/B/C must never be displayed to end users or substituted for their selected preference.

## Launch wording until P0 passes

Use "FixPilot beta", not "fully reliable repair service".
