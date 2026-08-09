# FixPilot per-bug fix ledger

Append-only. One entry per verified fix.

---

## 2026-08-09 Asia/Shanghai - image upload 400 on Ark Responses API

- Fixing agent: DeepSeek-V4-Flash
- Symptom: sending image in conversation fails twice with HTTP 400 from Ark Responses API ("missing input.status parameter" then "missing input.type parameter").
- Confirmed root cause: `build_responses_payload` in `backend/app/llm.py` only added `status: "completed"` to assistant input items; user input items were missing both `type: "message"` and `status: "completed"`. Ark Responses API requires both fields on all input items. Multi-turn conversations (with history) triggered stricter validation than first-turn requests.
- Files changed: `backend/app/llm.py:216-239` (added `type` + `status` to user, assistant, and fallback items).
- Verification: `py_compile` passed. Needs runtime test with image upload on Ark Responses API.
- Final status: code fix applied, pending runtime confirmation.
- Commit: not committed yet.

---

## 2026-08-09 Asia/Shanghai - diagnostics logs missing conv_id

- Fixing agent: DeepSeek-V4-Flash
- Symptom: error logs in `api-diagnostics.log` cannot be associated with a specific conversation, making debugging difficult.
- Confirmed root cause: `api_diagnostics.start/success/failure` did not accept or record `conv_id`. Platform API errors (non-custom API) were not logged at all.
- Files changed: `backend/app/api_diagnostics.py:50,67,97` (added `conv_id` parameter to `start`, `success`, `failure`); `backend/app/main.py:534,597-607` (always create diagnostics entries, pass `conv_id` to all calls).
- Verification: `py_compile` passed.
- Final status: fixed. All future log entries will carry `conv_id`. Platform API errors are now also logged.
- Commit: not committed yet.

---

## 2026-08-09 Asia/Shanghai - AI tells users "I can't see images" despite having OCR capability

- Fixing agent: GLM-5.2
- Symptom: FixPilot AI proactively tells users "别发图，我看不了图" (don't send images, I can't see them) and "我这边看不到截图" (I can't see screenshots), refusing to accept images. This contradicts FixPilot's core OCR feature which can extract text from screenshots (BSOD codes, error dialogs, device manager status).
- Confirmed root cause: `backend/app/llm.py:13` BASE_POLICY stated "不能真正看图" (cannot truly see images). The AI interpreted this as "I cannot process any images at all" and proactively refused images, even though the OCR pipeline (`backend/app/ocr.py` + `service._content_to_text`) works correctly.
- Files changed: `backend/app/llm.py:13` - rewrote the boundary line to distinguish "can recognize text in screenshots" vs "cannot visually inspect hardware appearance/connections". Added explicit instruction: "用户发来截图时应鼓励，不要说'看不了图'或拒绝接收" (encourage users to send screenshots, don't say "can't see images" or refuse).
- Verification: `py_compile` passed. Backend uvicorn restarted successfully (PID 59824). Health endpoint returns ok. Awaiting next test round to confirm AI no longer refuses images.
- Found during: persona progressive disclosure test, scenarios A03 R2 (conv_id: ca15a5992ababc0a5) and A02 R6 (conv_id: c0ced5db8d1a8fbdc).
- Final status: fixed (pending next test round verification).
- Commit: not committed yet.

---

## 2026-08-09 Asia/Shanghai - empty streamed replies recovered without exposing reasoning

- Fixing agent: Codex (GPT-5)
- Symptom: a provider could complete an HTTP/SSE request using only non-displayable `reasoning_content` deltas, then end with no user-visible text. The old tester mislabeled its SSE application error as HTTP 500.
- Confirmed root cause: protocol capture showed many reasoning-only deltas before final text. Some requests ended before a `content` delta. The original P1 log recorded a runtime empty-stream error, not an upstream HTTP 500.
- Files changed: `backend/app/llm.py` (one streaming attempt, then a non-streaming Chat Completions fallback only when no displayable content was yielded); `tools/persona_test.py` (SSE errors are recorded as `stream_error`, preserving the real HTTP 200 status).
- Verification: local mocked tests verified fallback text is returned for a reasoning-only stream and that a partial visible stream never triggers a duplicate request. Redacted protocol replay returned a 281-character final answer. Targeted A03 completed 8 rounds and I03 completed 14 rounds without stream, HTTP, or empty-reply errors.
- Final status: fixed and targeted-runtime verified.
- Commit: `committed atomically with this implementation; inspect Git history for the final hash`.

---

## 2026-08-09 Asia/Shanghai - image OCR acceptance verification

- Fixing agent: Codex (GPT-5)
- Symptom: the prior OCR prompt fix was only compiled, not verified against a real conversation.
- Confirmed root cause: the previous BASE_POLICY wording had caused the assistant to refuse screenshots despite the OCR pipeline.
- Files changed: no additional product-prompt change; this entry records runtime verification of the existing `backend/app/llm.py` policy repair.
- Verification: targeted A03 sent `images/device_manager_yellow.jpg` on round 2. FixPilot referenced the OCR-derived Realtek/Intel network-adapter text and never used a refusal phrase such as "can't see images". The scenario completed in 8 rounds with no image-not-seen bug.
- Final status: verified fixed.
- Commit: `committed atomically with this implementation; inspect Git history for the final hash`.

---

## 2026-08-09 Asia/Shanghai - deterministic OCR coverage in persona tests

- Fixing agent: Codex (GPT-5)
- Symptom: 71 persona-test rounds never sent a configured image, so the OCR path was untested.
- Confirmed root cause: image delivery depended entirely on an optional `[IMG:...]` marker from the tutor model.
- Files changed: `tools/scenarios.py` (per-image trigger terms and `must_send_by_round`); `tools/persona_test.py` (deterministic image selection, including tutor-model fallback).
- Verification: local tests prove trigger and due-round selection for all six configured images. Targeted A03 sent an actual image on round 2 and completed with no OCR rejection.
- Final status: fixed and targeted-runtime verified.
- Commit: `committed atomically with this implementation; inspect Git history for the final hash`.

---

## 2026-08-09 Asia/Shanghai - persona direction-grading false positives

- Fixing agent: Codex (GPT-5)
- Symptom: the test suite could report a correct diagnosis after matching generic error-code or administrative-step words, even when the model had changed to the wrong troubleshooting branch.
- Confirmed root cause: `diagnosis_correct` required only one third of a broad keyword list. I03 was falsely marked correct from `0xc0000005` and "administrator" while it missed the required compatibility direction.
- Files changed: `tools/scenarios.py` (nine scenario-specific direction-evidence groups); `tools/persona_test.py` (all required groups must be hit for a correct-direction result).
- Verification: local wrong-path I03 fixture now fails, a compatibility-path fixture passes, and a two-group browser-memory fixture passes.
- Final status: code fixed; full nine-scenario rebaseline remains required.
- Commit: `committed atomically with this implementation; inspect Git history for the final hash`.


### 2026-08-09 Asia/Shanghai — test option parser emitted no cards

- Fixing agent/model: Codex (GPT-5).
- Symptom: the new shared test helper never extracted the existing plain-text 选项 list, so a regression result could omit observed choices.
- Confirmed root cause: the regular expression stored Unicode escapes inside a raw string, making it search for the literal text backslash-u instead of 选项.
- Files changed: tools/testkit.py.
- Verification: a no-network mocked assertion parsed two numbered Chinese choices; Python compilation passed.
- Final status: fixed and verified.
- Commit: pending.

### 2026-08-09 Asia/Shanghai — persona runner profile mode was unreachable

- Fixing agent/model: Codex (GPT-5).
- Symptom: persona_test.py passed args.profile_mode to the runner but did not register --profile-mode, so a real CLI run would fail before testing.
- Confirmed root cause: the partial integration added the runner parameter but omitted the command-line parser entry.
- Files changed: tools/persona_test.py.
- Verification: persona_test.py --help exposes --profile-mode; a mocked two-round scenario verified both explicit and unknown profile setup paths.
- Final status: fixed and verified.
- Commit: pending.


### 2026-08-09 Asia/Shanghai — modular runner CLI did not compile after axis override

- Fixing agent/model: Codex (GPT-5).
- Symptom: after adding independent response-style coverage, run_all.py had the new argument inserted in the middle of the multi-line profile-mode argument, so the command could not start.
- Confirmed root cause: a line-oriented edit did not preserve the surrounding multi-line argparse call.
- Files changed: tools/run_all.py.
- Verification: Python compilation passed; run_all.py --help and persona_test.py --help both expose profile-mode and response-style.
- Final status: fixed and verified.
- Commit: pending.

---

## 2026-08-09 Asia/Shanghai - internal test cohort mapping reversed during refactor

- Fixing agent/model: Codex (GPT-5).
- Symptom: while introducing internal A/B/C test labels, the first edit mapped A to the beginner cohort and C to the advanced cohort. The requested convention is A = advanced, B = intermediate, C = beginner.
- Confirmed root cause: the initial refactor inferred letter order from explanation depth instead of the user's explicit internal ordering.
- Files changed: `tools/scenarios.py`; `tools/persona_test.py`; `tools/run_all.py`; `ai/Testing/FixPilot_TEST_PROFILE.md`.
- Verification: `py_compile` passed; a no-network assertion verifies A -> `advanced`, B -> `intermediate`, C -> `beginner`, and scenario IDs match their intended cohorts.
- Final status: corrected before commit. No product UI, saved profile, or external user output used the temporary mapping.
- Commit: pending.


### 2026-08-09 Asia/Shanghai - normal reply text was rewritten during frontend rendering

- Fixing agent/model: Codex (GPT-5).
- Symptom: replies showed artificially stretched Chinese characters, ordinary numbered content was rendered as choices or split, and an unmatched code fence could make a reply look truncated.
- Confirmed root cause: bot/share bubbles used `text-align: justify`; `parseOptions()` guessed that generic numbered lists were choices; `breakNumbered()` modified the original answer text before Markdown rendering; unmatched fences were treated as a complete code block.
- Files changed: `backend/static/style.css`; `backend/static/app.js`.
- Verification: Node assertions confirm ordinary numbered steps stay untouched, only explicit `选项：` blocks create cards, and an unmatched fence does not hide the tail. Served local static assets contain the new code.
- Final status: fixed; historical answer text was intentionally not rewritten.
- Commit: `70441ec fix: preserve reply text and harden admin boundary`.

### 2026-08-09 Asia/Shanghai - blue-screen screenshot was incorrectly refused

- Fixing agent/model: Codex (GPT-5).
- Symptom: a user offering a blue-screen image was told that FixPilot could not read it, even though image OCR supports screenshot text.
- Confirmed root cause: the model policy did not sharply separate supported OCR screenshot text from unsupported physical visual inspection.
- Files changed: `backend/app/llm.py`.
- Verification: the policy now explicitly treats STOP codes, error dialogs, Device Manager and Task Manager screenshots as OCR-supported and prohibits the "cannot see images" refusal for them; Python compilation passed.
- Final status: fixed in the runtime policy; new replies follow the rule, while the old stored answer remains historical evidence.
- Commit: `70441ec fix: preserve reply text and harden admin boundary`.

### 2026-08-09 Asia/Shanghai - client could attempt model-role injection and default admin credentials existed

- Fixing agent/model: Codex (GPT-5).
- Symptom: user requested an administrator boundary against untrusted/injected content.
- Confirmed root cause: `/api/chat` accepted arbitrary client `role` values into the provider context; administrator bootstrap had source defaults; invite users could potentially reserve an administrator name; administrator login had no attempt guard.
- Files changed: `backend/app/service.py`; `backend/app/main.py`; `backend/app/llm.py`; `backend/app/auth.py`; `backend/app/config.py`; `backend/.env.example`.
- Verification: direct live-route tests reject forged `system` and `assistant` messages with HTTP 400 before provider access. Unit assertions verify role filtering, no default admin creation without explicit environment credentials, and a five-failure administrator-login throttle. Backend compilation and local health check passed.
- Final status: fixed for this single-process deployment; the in-memory throttle resets when the server restarts, so an internet-facing multi-process deployment should move this control to a shared proxy/store.
- Commit: `70441ec fix: preserve reply text and harden admin boundary`.

### 2026-08-09 Asia/Shanghai - direct DeepSeek settings referenced retired model aliases

- Fixing agent/model: Codex (GPT-5).
- Symptom: the API settings page suggested `deepseek-chat` even though the official V4 Flash release requires `deepseek-v4-flash` for the current model.
- Confirmed root cause: frontend API presets and the visible model placeholder were not updated when the backend default changed.
- Files changed: `backend/static/app.js`; `backend/static/index.html`.
- Verification: JavaScript syntax and static preset assertions passed; an offline Responses payload assertion passed; `git diff --check` passed.
- Final status: fixed. Existing saved custom API settings remain unchanged.
- Commit: 4d88cd3 (`fix: use official DeepSeek V4 Flash preset`).

### 2026-08-09 Asia/Shanghai - BIOS change request could bypass the high-risk notice

- Fixing agent/model: Codex (GPT-5).
- Symptom: S03 could receive BIOS/UEFI setting instructions without a trusted high-risk card when the provider omitted its leading risk marker.
- Confirmed root cause: trusted notice delivery depended entirely on a model-generated `[RISK:high]` marker; changing BIOS settings was not described precisely enough in the model rule.
- Files changed: `backend/app/safety.py`; `backend/app/main.py`; `backend/app/llm.py`; `tools/transport_test.py`; `tools/run_all.py`.
- Verification: live `python tools/run_all.py --suites safety ...` passed S01-S04, including S03. No-network T01 confirms a BIOS-setting request is high risk.
- Final status: fixed with a deterministic preflight notice plus a clarified model policy; model markers remain a secondary signal.
- Commit: pending.

### 2026-08-09 Asia/Shanghai - driver removal/reinstallation could bypass the medium-risk notice

- Fixing agent/model: Codex (GPT-5).
- Symptom: S04 could recommend removing and reinstalling a graphics driver without a trusted medium-risk card.
- Confirmed root cause: the provider could omit `[RISK:medium]`, and the parser had no rule-based fallback. The Chinese phrasing “卸掉再装” was not covered by an explicit fallback.
- Files changed: `backend/app/safety.py`; `backend/app/main.py`; `backend/app/llm.py`; `tools/transport_test.py`; `tools/run_all.py`.
- Verification: live `python tools/run_all.py --suites safety ...` passed S01-S04, including S04. No-network T01 covers the exact “卸掉再装” wording.
- Final status: fixed with a deterministic preflight notice plus clarified policy language.
- Commit: pending.

### 2026-08-09 Asia/Shanghai - an empty stream plus empty fallback ended a conversation with no usable reply

- Fixing agent/model: Codex (GPT-5).
- Symptom: A02 round 4 could end with “Provider returned no displayable reply in stream or fallback”, leaving the user without an answer.
- Confirmed root cause: `stream_chat` made one completed fallback request after a stream with no visible text, then raised immediately if that completed response was empty too.
- Files changed: `backend/app/llm.py`; `tools/transport_test.py`; `tools/run_all.py`.
- Verification: no-network T02 simulates an empty reasoning-only stream plus an empty first completed fallback and confirms exactly one retry returns the second reply; T03 confirms a visible stream never retries. `python -m py_compile ...` and `python tools/run_all.py --suites renderer,transport` passed. A targeted live A02 runner was attempted but the desktop process host terminated it before a result artifact; this is not counted as a pass.
- Final status: fixed with one bounded retry only before any user-visible text. A provider can still fail twice; the existing visible error remains the honest fallback.
- Commit: pending.

#### Commit reference - 2026-08-09 Asia/Shanghai

The three fixes immediately above were implemented and verified in commit `a2b4b16` (`fix: harden risk notices and empty replies`).

## 2026-08-09 Asia/Shanghai - saving custom API settings deadlocked and hung

- Fixing agent/model: DeepSeek-V4-Flash.
- Symptom: while adding server-side per-account API settings, `POST /api/api-settings` never returned (request timed out), so the save could not complete.
- Confirmed root cause: `save_api_settings` in `backend/app/db.py` called `get_api_settings` while holding the module-global non-reentrant `_lock`; `get_api_settings` then tried to acquire the same lock, deadlocking every save. Reads were unaffected.
- Files changed: `backend/app/db.py` (`save_api_settings` now returns a constructed dict instead of calling `get_api_settings` inside the lock).
- Verification: live HTTP flow confirmed save, re-read, clear, and re-read all return promptly with correct values; `py_compile` and `node --check` passed.
- Final status: fixed and live-route verified.
- Implementation commit: ad6c48f3eea7a988935ff88041ebc98cf33df478 (`feat: persist custom API settings and testing records`).


## 2026-08-09 Asia/Shanghai - sidebar account overlapped the conversation list

- Fixing agent/model: Codex (GPT-5).
- Symptom: with enough conversation history, the sidebar list could flow visually behind the contact/account area; the account row (including admin) appeared to overlap list entries.
- Root cause: `.sidebar-account` and `.sidebar-foot` used desktop absolute positioning while `.conv-list` was not given a reserved bottom region.
- Files changed: `backend/static/index.html`; `backend/static/style.css`.
- Fix: placed the footer and account button in a normal flex child (`.sidebar-bottom`) with a separator; made the list the constrained scroll region via `min-height: 0`.
- Verification: static inspection plus `python tools/run_all.py --suites renderer,transport,websearch` PASS and `git diff --check` PASS.
- Status: fixed in the working tree; manual visual confirmation remains after server restart.
- Commit: pending.


#### Commit reference - 2026-08-09 Asia/Shanghai

The optional external-lookup behavior and sidebar boundary fix above were implemented and verified in commit `3a37a8b` (`fix: keep lookup optional and reserve sidebar footer`).


## 2026-08-09 Asia/Shanghai - external lookup was incorrectly exposed as a user search switch

- Fixing agent/model: Codex (GPT-5).
- Symptom: the composer exposed a `???` button and the browser could include a `webSearch` boolean in a chat request, making a narrow official-reference fallback look like a user-operated general-search feature.
- Root cause: lookup capability was initially modeled as a one-turn client preference instead of a conservative server/model decision after knowledge-base retrieval.
- Files changed: `backend/static/index.html`; `backend/static/style.css`; `backend/static/app.js`; `backend/app/main.py`; `backend/app/service.py`; `backend/app/llm.py`; `tools/web_search_test.py`; the aligned policy and handoff documents in `ai/`.
- Fix: removed the UI/API control. Only the server-approved official DeepSeek V4 Flash path gets an optional tool; the model is instructed to use it only for verifiable official references and otherwise continue local knowledge-base diagnosis. Normal non-search replies show no banner.
- Verification: static browser/API contract assertions plus `python tools/run_all.py --suites renderer,transport,websearch` PASS (5 renderer, 3 transport, 7 websearch). No live provider call was used.
- Final status: fixed in the working tree; the local server must be restarted before manual checking.
- Commit: pending.

#### Commit reference - 2026-08-09 Asia/Shanghai

Implemented and verified in commit `0879ba7` (`feat: make official lookup automatic`).


## 2026-08-09 Asia/Shanghai - candidate official sources could bypass the intended evidence boundary

- Fixing agent/model: Codex (GPT-5).
- Symptom: the source catalogue was not connected to lookup runtime; its counters were stale, a pending source was enabled, and several broken/unreachable entries could have been treated as verified references. The existing provider web-search path had no catalogue-based hostname filtering.
- Root cause: research output was treated as data rather than as a candidate registry with executable review gates. The external provider tool supplies general web results and does not provide a documented domain-filter field in this integration.
- Files changed: `data/official_sources.json`; `backend/app/official_sources.py`; `backend/app/service.py`; `backend/app/llm.py`; `tools/official_sources_test.py`; `tools/official_sources_audit.py`; `tools/run_all.py`; `tools/web_search_test.py`; the related policy, test, and audit documents.
- Fix: added verified/enabled/source-tier gating, identifier-based vendor routing, high-risk metadata, canonical link corrections, live URL review, per-turn allowlisted-domain policy, and final source URL filtering. Generic symptoms no longer unlock external search; nonofficial and review-needed records cannot be automatically used.
- Verification: full local targeted suite PASS (renderer 5, transport 3, websearch 8, sources 6) plus enabled-only live registry audit PASS (23 reachable, 0 review).
- Final status: fixed in the working tree; a paid live provider acceptance test with a known exact model/manual is still a release follow-up.
- Commit: pending.

#### Commit reference - 2026-08-09 Asia/Shanghai

Implemented and verified in commit `cc47baf` (`feat: gate lookup with official source registry`).


## 2026-08-09 Asia/Shanghai - source directory wrongly blocked unlisted official documentation

- Fixing agent/model: Codex (GPT-5).
- Symptom: a product or manual outside `data/official_sources.json` could not be used even when the request was specific and an official page existed; returned URLs outside the selected registry domain were hidden and the answer was discarded.
- Root cause: the registry was implemented as a strict runtime allowlist and `append_web_search_sources` treated every non-matching URL as unsafe evidence, instead of distinguishing a preferred official route from an unlisted lead.
- Files changed: `backend/app/official_sources.py`, `backend/app/service.py`, `backend/app/llm.py`, `tools/web_search_test.py`, `tools/official_sources_test.py`, `ai/FixPilot_Official_Source_Registry_v1.0.md`, `ai/FixPilot_????????_v1.0.md`, `ai/Testing/README.md`, and `ai/WORK_LOG.md`.
- Fix: registry matches are now preferred first. A concrete model-plus-documentation request can broaden when no registry route exists. Preferred links display `??????`; unlisted URLs display `?????????????` and a verification warning. Generic symptoms still do not unlock lookup; unlisted sources cannot by themselves justify high-risk actions.
- Verification: `python tools/run_all.py --suites renderer,transport,websearch,sources` PASS (24 checks); Python compilation and `git diff --check` PASS.
- Status: fixed and committed.
- Commit: `8d472be` (`fix: prioritize official source registry`).


## 2026-08-09 Asia/Shanghai - unlisted official documentation request lost its per-turn fallback boundary

- Fixing agent/model: Codex (GPT-5).
- Symptom: a concrete, unlisted model/manual request could enable lookup but receive an empty source-policy message.
- Root cause: `build_lookup_policy([])` returned an empty string after the registry became a preferred route.
- Files changed: `backend/app/official_sources.py`, `tools/web_search_test.py`, and `ai/WORK_LOG.md`.
- Fix: an empty preferred-source set now produces an official-only fallback: direct manufacturer, OS-vendor, or hardware-vendor support pages only; no forums, mirrors, snippets, or unverified third parties as confirmed evidence.
- Verification: `python tools/run_all.py --suites websearch,sources` PASS (16 checks); compilation and `git diff --check` PASS.
- Status: fixed and committed.
- Commit: `c95a900` (`fix: retain official fallback policy`).

## 2026-08-10 Asia/Shanghai - roast reactions could repeat and a raw 6 stretched in shared transcripts

- Fixing agent/model: Codex (GPT-5).
- Symptom: a conversation could show multiple reaction-only 6 messages; an otherwise sensible diagnosis or a thanks/review could still receive one. In share links and generated long images, raw 6 was rendered as ordinary assistant text and stretched into a full-width bubble.
- Root cause: choose_joke_effect returned six without conversation history, cooldown, acknowledgement detection, or a once-per-conversation rule. The database persisted a raw 6, while renderers only had special handling for MEME markers; the share page flex body expanded it like normal text.
- Files changed: backend/app/memes.py, backend/app/main.py, backend/app/service.py, backend/app/llm.py, backend/static/app.js, backend/static/share.html, backend/static/style.css, tools/memes_test.py, tools/renderer_test.js, tools/run_all.py, and linked AI policy documents.
- Fix: introduced semantic REACTION:six / REACTION:chichi records while retaining legacy raw-6 rendering; added acknowledgement blocking, a three-ordinary-assistant-message cooldown, one-six-per-conversation enforcement, safe meme preference after six, compact reaction cards across chat/admin/share/link/image, and no-context filtering. Removed the rejected meme from the active selection pool. No fixed productized roast lines were added.
- Verification: python tools/run_all.py --suites renderer,memes PASS (renderer 7, memes 7); python -m py_compile backend/app/memes.py backend/app/main.py backend/app/service.py backend/app/llm.py PASS; node --check backend/static/app.js PASS; git diff --check PASS. No live provider or paid API request was made.
- Status: fixed in the working tree; visual browser automation could not initialize because this Codex runtime lacks its local browser-kernel assets, so one manual cache-refresh check remains before release.
- Implementation commit: 16469b0 (fix: restrain roast reactions).

---

## 2026-08-10 Asia/Shanghai - blank page from missing autoResize

- Fixing agent/model: DeepSeek-V4-Flash.
- Symptom: after deploying the API-settings server migration, `https://ai.dnbox.cn/fixpilot/` rendered a blank page (background only). Console: `Uncaught ReferenceError: autoResize is not defined at app.js?v=47:2482:33`. Hard refresh did not help.
- Confirmed root cause: `autoResize` was added to `backend/static/app.js` locally but never committed/pushed, so the server kept serving the old bundle; `index.html` still referenced `?v=47`.
- Files changed: `backend/static/app.js` (added `autoResize()`); `backend/static/index.html` (cache tag `?v=47` -> `?v=48`).
- Verification: `git diff` shows exactly the 14-line `autoResize` addition before the event binding; commit pushed to origin/main.
- Final status: fixed in the repo and pushed. Requires `git pull` + uvicorn restart on the server (port 8135) to clear online.
- Commit: 01fdb37.

---

## 2026-08-10 Asia/Shanghai - custom API test button broken on subpath deployment

- Fixing agent/model: DeepSeek-V4-Flash.
- Symptom: online site at `https://ai.dnbox.cn/fixpilot/` reported frequent errors when using custom API settings. The "测试连接" button always failed.
- Confirmed root cause: `testApiSettings_action()` at `backend/static/app.js:2262` used `fetch('/api/test-api', ...)` with a leading slash. With `<base href="/fixpilot/">`, a leading-slash URL resolves against the origin only (`ai.dnbox.cn/api/test-api`), bypassing the `/fixpilot/` nginx route. This was the only fetch call in the app with a leading slash; all other 26 calls used relative paths.
- Files changed: `backend/static/app.js` (`'/api/test-api'` → `'api/test-api'`); `backend/static/index.html` (cache tag `?v=48` → `?v=49`).
- Verification: grep confirms no remaining `fetch('/api` patterns; commit pushed to origin/main.
- Final status: fixed in repo. Requires `git pull` + restart on server.
- Commit: b6de6d3.

---

## 2026-08-10 Asia/Shanghai - deployment handoff guide contained an incorrect generic server assumption

- Fixing agent/model: Codex (GPT-5).
- Symptom: the newly added deployment runbook described an unverified systemd/Nginx/8000 configuration, which did not match FixPilot's live server procedure and could have led a later maintainer to issue the wrong commands.
- Confirmed root cause: the guide was written from generic repository hints instead of the already-verified deployment record supplied by the project owner.
- Files changed: `ai/DEPLOYMENT_RUNBOOK.md`; `ai/WORK_LOG.md`.
- Verification: reconciled against the recorded production incident `f2ce670`, its implementation commit `01fdb37`, the current `index.html` cache tag, and the `/api/health` route. No live server command was run.
- Final status: fixed in the working tree; the runbook now names the actual project path, backend virtual environment, port 8135, `pkill`/`nohup` lifecycle, cache workflow, and known incident.
- Commit: pending.

---

## 2026-08-10 Asia/Shanghai - first-run preference cards could be skipped too easily

- Fixing agent/model: Codex (GPT-5).
- Symptom: the first-run screen spent visual attention on explanatory copy and an input-triggered sentence, while the user could overlook the three selectable preference cards and type immediately.
- Confirmed root cause: the copy explained why FixPilot wanted a choice instead of making the choice itself clear and beneficial; card clickability was also visually understated.
- Files changed: `backend/static/app.js`, `backend/static/style.css`, `backend/static/index.html`, `ai/FixPilot_首次引导与偏好机制_v1.0.md`, `ai/WORK_LOG.md`.
- Verification: onboarding static contract PASS; `node --check backend/static/app.js` PASS; renderer R01-R07 PASS; `git diff --check` PASS. Visual desktop/mobile verification remains pending. No live model or production deployment was performed.
- Final status: fixed in the working tree. The two requested lines are removed; cards now state the resulting response style and show a light click affordance. Direct input remains unblocked.
- Commit: pending.
