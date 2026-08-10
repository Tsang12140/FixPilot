# FixPilot agent working agreement

## Non-negotiable: commit and push only on explicit instruction

默认不提交、不推送。代码改动只保留在本地工作区，本地浏览器能直接看到效果即可，不需要为了"同步"而频繁 commit / push。

只有用户明确说出 commit / 提交 / push / 推送 等指令时，才执行 `git commit` 和 `git push`。即使改动已完成、已通过验证，也不得擅自提交推送。

这与 `ai/WORK_LOG.md` 和 `reports/fixed.md` 的记录义务不冲突：记录照常写入本地文件，但提交推送仍以用户显式指令为准。

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


## Test workflow trigger

When the user says “我要测试”, “跑测试”, “回归测试”, “测一下”, or
otherwise asks to test a change, treat it as a product-validation request — not
a request to run only compilation/static checks.

Before selecting or running tests, read:

1. ai/Testing/README.md;
2. ai/Testing/TESTING_PLAYBOOK.md; and
3. the current project profile, ai/Testing/FixPilot_TEST_PROFILE.md.

Choose the smallest sufficient module set from that profile, state whether a
live/paid model call is involved, preserve a structured result artifact, and
classify outcomes as PASS, FAIL, ERROR, or REVIEW. ERROR/REVIEW must never be
reported as passed. For a real bug fix, retain the existing requirements for
reports/fixed.md, a batch report where applicable, and ai/WORK_LOG.md.

For another project, copy the testing playbook, the project-profile template,
and this trigger section into that repository before asking an AI to “test”.
