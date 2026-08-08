# FixPilot agent working agreement

## Non-negotiable handoff log

Before changing this repository, read `ai/WORK_LOG.md` and the relevant product rule in `ai/`.

Every completed task, especially a bug fix, must append an entry to `ai/WORK_LOG.md` before the task is committed or handed back. The entry must record: request/problem, root cause or investigation result, files changed, verification performed, commit hash when available, and remaining risks or follow-ups. Never replace or silently delete older entries. Never include passwords, API keys, access tokens, or other secrets.

No implementation commit is complete unless its matching work-log entry is staged with it. If a task cannot be verified, state that clearly in the entry instead of implying success.
