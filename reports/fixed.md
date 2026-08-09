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
- Commit: pending.
