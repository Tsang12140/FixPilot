# FixPilot verified fix ledger

This is the append-only ledger for individual bugs that have been fixed and
verified. Add an entry only after the repair has passed its relevant checks.

It complements, rather than replaces:

- `ai/WORK_LOG.md` for task handoff; and
- `reports/reportYYYYMMDD_NNN.md` for a full batch-search or batch-repair report.

### 2026-08-09 11:18 Asia/Shanghai - Send click misclassified as retry

- Agent/model: Codex (GPT-5)
- Discovered: 2026-08-09 11:18 Asia/Shanghai
- Fixed: 2026-08-09 11:18 Asia/Shanghai
- Symptom: Clicking Send in a newly created conversation showed the warning to
  return to the original conversation and did not send the typed message.
- Root cause: `addEventListener('click', send)` passed a DOM `MouseEvent` as
  `send(retryState)`. The old truthiness check treated that event as retry
  state, then rejected it because it had no conversation ID.
- Files changed: `backend/static/app.js`; `AGENTS.md`; `reports/fixed.md`.
- Verification: A headless-browser click on Send made exactly one `/api/chat`
  request for `c-send-regression` with the typed text, showed no incorrect
  retry toast, and left Send enabled. `node --check backend/static/app.js`
  and `git diff --check` passed.
- Status: verified fixed.
- Commit: pending.

## Entry template

### YYYY-MM-DD HH:MM Asia/Shanghai - short bug title

- Agent/model:
- Discovered:
- Fixed:
- Symptom:
- Root cause:
- Files changed:
- Verification:
- Status:
- Commit:
