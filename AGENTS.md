# FixPilot agent working agreement

## Non-negotiable handoff log

Before changing this repository, read `ai/WORK_LOG.md` and the relevant product rule in `ai/`.

Every completed task, especially a bug fix, must append an entry to `ai/WORK_LOG.md` before the task is committed or handed back. The entry must record: request/problem, root cause or investigation result, files changed, verification performed, commit hash when available, and remaining risks or follow-ups. Never replace or silently delete older entries. Never include passwords, API keys, access tokens, or other secrets.

No implementation commit is complete unless its matching work-log entry is staged with it. If a task cannot be verified, state that clearly in the entry instead of implying success.

## Non-negotiable per-bug fix ledger

After every bug is actually fixed and verified, append one concise event to
`reports/fixed.md` before committing or handing back. Create the file if it
does not exist. This applies to one-line UI, API, state, rendering, and data
bugs just as much as larger fixes.

Each entry must include: discovered/fixed date and timezone, the fixing
agent/model, symptom, confirmed root cause, files changed, verification, final
status, and commit hash when available. Never record secrets. Do not record an
unfixed suspicion as fixed; if verification fails, state that in `WORK_LOG.md`
instead.

This is an append-only per-event ledger, not a replacement for either required
record below:

- `ai/WORK_LOG.md` remains the task-level handoff log for every completed task.
- `reports/reportYYYYMMDD_NNN.md` remains the detailed report required after a
  batch search or batch repair. It may reference the relevant `fixed.md`
  entries instead of duplicating their short event summaries.

When a batch repairs several bugs, write both: one `fixed.md` entry for every
verified individual fix and one batch report containing the complete findings,
coverage, regression result, and remaining risks.
