# FixPilot work log and AI handoff

> Status: living project record. This file is the required first read for an AI
> continuing work in this repository. It complements (but does not replace) the
> product-rule documents in this folder.
>
> Last consolidated: 2026-08-09.

## Mandatory update rule

The repository-level rule is also in [`../AGENTS.md`](../AGENTS.md). Every AI
must append a dated entry here after completing a task and before committing or
handing it back. This is mandatory for bug fixes as well as new features.

Each entry must state:

1. the user-visible request or bug;
2. the finding/root cause (or explicitly say that it is still unknown);
3. the exact files or components changed;
4. validation actually run, including failed or unrun checks;
5. the commit hash when it is available; and
6. follow-ups, regressions to watch for, and diagnostic IDs if applicable.

Never rewrite or delete a historical entry merely to make the log shorter. Do
not put API keys, passwords, tokens, cookies, or other secrets in this file.

## Current product map

- Application: a FastAPI computer-troubleshooting assistant. The browser UI is
  plain HTML/CSS/JS in `backend/static/`; the backend lives in `backend/app/`.
- Main UI files: `backend/static/index.html`, `backend/static/style.css`, and
  `backend/static/app.js`.
- Core experience: focused diagnostic questioning, RAG, local OCR, history,
  image upload, shared conversation pages, invitation/account flow, usage
  quotas, and selectable built-in/custom AI models.
- Product behavior rules and planned AI policy are in the `ai/` folder. Treat
  these as specifications, not proof that every phase has been implemented;
  inspect code before claiming a rule is live.
- Current product priorities: one key diagnostic question at a time, do not
  present guesses as facts, preserve user control, and never downgrade safety
  warnings because a user selected concise or roast style.

## Important current behavior to preserve

### Conversation and UI

- Quick-question chips must send exactly the text displayed on the chip. Never
  silently add details such as "but the fan is spinning" to a generic "black
  screen on boot" chip.
- The assistant's numbered answer options are parsed into clickable cards. The
  parser must not split an ordinary numbered procedure into fake choices.
- Meme replies and the existing `6` easter egg are contextual/randomized
  assistant behavior, not user messages. Meme assets must be served from stable
  project URLs and their timestamps must line up with the image bubble.
- A blank/failed reply must leave a clear recoverable message rather than an
  empty gap. Preserve the user message and allow the conversation to continue.
- The desktop model picker stays beside the composer. On mobile, it belongs in
  the top bar because focusing the input opens the keyboard.
- Mobile composer default height is one text line (34px textarea). It may grow
  while the user types, up to 96px; it must not return to the former tall,
  two-row idle layout.
- On mobile the model name remains full when it fits. It falls back to a short
  label (for DeepSeek, `DS`) only when the header truly lacks room, and hides
  the arrow only as a final fallback. The dropdown opens below the top bar.

### Account, settings, and model configuration

- Clicking settings must open the Account tab by default on desktop and mobile.
  Do not pass a DOM click event as the requested tab name.
- The account card contains the avatar and username. The avatar edit control
  expands the full avatar grid; selecting one collapses it. Logout belongs in
  the account section, not as a stray side-nav action.
- Preserve the About page's existing external links/star material when changing
  its explanatory copy.
- Settings has Account, API, Preferences, and About tabs. Keep the tab styling
  visibly integrated with the content panel and aligned across tabs.
- The model menu separates built-in and custom models. A configured custom
  model must appear in the custom section; built-in display name must reflect
  the actual configured platform model rather than a marketing placeholder.
- API setup supports presets and fully custom OpenAI-compatible endpoints.
  Explicitly test a configuration before marking it active. Do not log any
  credentials.

### Safety and AI behavior

- User technical level and response style are different axes. Style changes
  delivery, never factual or safety standards.
- Safety notices are risk-tiered. Medium-risk changes to drivers/system/device
  state and high-risk changes that may affect data, boot, firmware, or hardware
  must be presented in the assistant answer with the warning treatment.
- Do not ask inexperienced users to bridge a PSU/24-pin connector casually.
  The prior behavior was changed to block that as a beginner step.
- The product documents define future profile inference, prompt layers,
  diagnostic confidence, and safety governance. Implement only after checking
  current code and adding focused tests.

## Chronological work record

### 2026-08-07 - foundation

- `69f57c5` - Created FixPilot: FastAPI backend, DeepSeek integration, RAG,
  local OCR, and the initial one-question-at-a-time troubleshooting UI.

### 2026-08-08 - product personality, chat interaction, and custom API work

- `6067bd9` - Refreshed the login visual, favicon, and browser compatibility.
- `62a0ffe` - Added the first personalized-support behavior and preference
  foundation.
- `c58aabf` - Added contextual meme easter eggs.
- `0bc890a` - Fixed meme assets so chat and share pages load them through stable
  URLs instead of fragile local references.
- `0f8928a` - Restored resilient clickable diagnostic option cards after option
  rendering/splitting problems.
- `aa1f1ef` - Added Volcengine Ark API settings.
- `1a0cd06` - Aligned timestamps for memes and shared conversations.
- `1f5169e` - Accepted complete OpenAI-compatible endpoint URLs instead of
  forcing a single provider shape.
- `e1a1c53` - Corrected Ark connectivity testing.
- `d3b051b` - Added safe custom-API diagnostics for failures.
- `b4eb135` - Split connection testing from saving API settings and refined the
  roast persona behavior.
- `8c1c619` - Prevented blank replies in share pages.
- `f15214c` - Switched the API probe to a non-streaming request so a successful
  connection test is reliably observable.
- `23fab9c` - Normalized custom API keys before a request.
- `29e7e15` and `74468ed` - Corrected proxy handling for Volcengine Ark,
  including use of the system HTTPS proxy where needed.
- `10a08c2` - Added support for Responses API endpoints in addition to chat
  completions.
- `806ed8e` - Closed the settings modal automatically after account binding.
- `bd781a9` - Simplified the Volcengine Responses setup flow.
- `c63f27b` - Added full custom API configuration.
- `e858152` - Made a successfully tested API configuration become active.
- `fcc96c3` - Added the default model picker and made the composer more compact.
- `d797335` - Fixed model-picker visibility and composer sizing.

### 2026-08-09 - model picker, settings, resiliency, safety, and mobile polish

- `221bcf6` - Refined composer alignment and model-picker visibility after
  long-name/layout issues.
- `283c599` - Anchored the model menu and clamped long model names.
- `d688bd7` - Showed the actually configured platform model in the picker.
- `ad0389b` - Separated built-in and custom models in the picker.
- `eec7f36` - Made Preferences show the mode-specific explanatory copy:
  Normal / Roast / Concise, instead of showing roast copy for every mode.
- `9294888` - Replaced the main About copy with the FixPilot problem statement.
- `715fc9d` - Restored existing About links/star content that was accidentally
  removed while changing the copy.
- `9cc6bb3` - Added sidebar search and made the avatar + username entry open
  settings.
- `c9bd93e` - Improved handling of blank replies and reduced the account avatar
  grid to an expandable interaction.
- `0dc07e9` - Added recovery messaging for interrupted model replies rather
  than leaving a silent conversational gap.
- `1e9f80a` - Fixed Responses API follow-up payloads by carrying the required
  completed-state input correctly.
- `9c7147c` - Simplified avatar editing and prevented casual PSU-jumper
  instructions for beginner-level users.
- `16403f8` - Added the product-level risk-aware safety guardrails and answer
  warning treatment.
- `68422fd` - Streamlined mobile header controls and mobile chat appearance.
- `c4e96f5` - Tightened mobile bubbles/settings and fixed mobile settings
  rendering behavior.
- `15d8ee9` - Fixed settings opening blank: the click event had been treated as
  a tab name. Settings now defaults to Account; logout is in that account area.
- `4cf92e3` - Improved settings tab integration/alignment and restored generic
  quick-question payloads.
- `29cda34` - Generalized quick-question handling to one source of truth so all
  chips display and send the identical payload.
- `85dee80` - Put the mobile model picker back in the stable top bar, implemented
  responsive full-name -> abbreviation behavior, made the idle composer
  one-line high, and constrained typed expansion. Verified with Playwright at
  767, 540, 480, 430, 420, 390, 360, 320, and 280px: no page errors or
  horizontal overflow; menu stayed in viewport and below the header.

### 2026-08-11 - 对话界面顶栏与移动端侧栏 logo 统一为 d0c1319 纯色幽灵

- 需求：将对话界面左上角（顶栏）与移动端侧栏左上角的 logo 也换成 commit
  `d0c1319` 版本的纯色幽灵（白身、深蓝描边、椭圆眼、三条天线、无彩色装饰）。
- 现状：顶栏用 `assets/fixpilot-logo-lockup-v2.*`（幽灵 + 蓝紫渐变文字），
  侧栏用 `assets/fixpilot-logo-mark-v2.*`（幽灵带彩色装饰），与 d0c1319 纯幽灵不一致。
- 改动：
  - 生成 `backend/static/assets/fixpilot-logo-mark-v3.{png,webp}`（192x192 纯幽灵，
    用 sharp 渲染自 `logo.svg` 提取的 d0c1319 path）。
  - 生成 `backend/static/assets/fixpilot-logo-lockup-v3.{png,webp}`（512x180，
    幽灵 + 深色 #1D2233 'FixPilot' 文字，用 msyhbd 字体，非彩色渐变）。
  - 更新 `backend/static/index.html`：`.sidebar-brand-mark` → mark-v3、
    `.topbar-brand-lockup` → lockup-v3。
  - 删除已不再引用的 v2 图片文件。
- 验证：服务端 8010 端口返回的 index.html 含 v3 且无 v2 引用；v3 资源 HTTP 200；
  浏览器清缓存后确认顶栏 `.topbar-brand-lockup` 指向 fixpilot-logo-lockup-v3、
  移动端侧栏 `.sidebar-brand-mark` 指向 fixpilot-logo-mark-v3，外观为纯白幽灵 + 深色文字。
- commit：尚未提交（按约定仅在用户显式要求时提交）。
- 跟进：无。

## Known investigation notes

- Custom model providers differ materially. A successful request in another
  client does not prove this app is sending the same endpoint, protocol, model
  ID, stream mode, or proxy path. Use the app's API test control and diagnostic
  IDs/logs before changing request code. Do not guess from a 400 alone.
- Responses API and Chat Completions API have different payload shapes. Keep
  their adapters separate; a fix for one must be tested as a multi-turn chat.
- The picker and composer are responsive hotspots. Any change must be checked
  on both desktop and at least 390px and 320px mobile widths, with the dropdown
  open and the input focused/filled.
- Static asset version query strings in `index.html` are intentionally bumped
  when changing `app.js` or `style.css` so browser cache does not mask a fix.

### 2026-08-09 - establish persistent AI handoff logging

- Request / symptom: the project needed a durable record of completed work and
  bug investigations so a later AI can continue without repeating the same
  failures or removing already-required changes.
- Finding / root cause: prior work existed only in chat context and commit
  subjects; there was no repository-level instruction requiring future agents
  to preserve a task-by-task record.
- Changed:
  - `AGENTS.md` - established the non-negotiable rule to read and update the
    work log for every task.
  - `ai/WORK_LOG.md` - added the current project map, behavioral invariants,
    chronological history, diagnostics notes, and append template.
  - `ai/README_交接索引.md` - added the required reading link to the
    rule and work log.
- Verified: reviewed full Git history from `69f57c5` through `85dee80`; the
  working agreement explicitly prohibits secrets and historical rewrites.
- Commit: documentation commit pending.
- Follow-up / risk: every future AI must update this file in the same commit as
  implementation work; a stale log is a defect and must be corrected first.

### 2026-08-09 - P1: repair corrupted risk-notice Chinese and add client fallback

- Request / symptom: medium- and high-risk warning cards displayed literal
  question marks. The defect affected every safety notice sent by the backend.
- Finding / root cause: `backend/app/safety.py` introduced in `16403f8` stored
  the title/message as ASCII question marks, not as a display encoding issue.
  The frontend used `notice.title || safe.title`; the corrupted but non-empty
  strings were truthy, so they replaced the frontend's correct local fallback.
- Changed:
  - `backend/app/safety.py` - restored correct UTF-8 medium/high title and
    message values.
  - `backend/static/app.js` - added `safeRiskCopy`, which treats strings made
    only of ASCII/full-width question marks and whitespace as invalid and uses
    the trusted local fallback.
  - `backend/static/index.html` - bumped the JS cache version.
- Verified:
  - backend unit check asserted exact Chinese values, no question marks, and
    `json.dumps(..., ensure_ascii=False)` payload content for both levels;
  - Python compiled `safety.py` and `main.py`;
  - browser test passed a corrupted `{title: '?????', message: '????'}` notice
    into `riskNoticeHtml` and verified it rendered the Chinese fallback while
    preserving valid server text.
- Commit: pending.
- Follow-up / risk: retain the frontend guard even though the backend is fixed;
  external/old servers or a future bad write must never turn a safety warning
  into question marks again.

### 2026-08-09 - relocate desktop sidebar toggle and model control

- Request / symptom: the desktop sidebar toggle was in the top bar, and the
  model picker shared the lower-right action cluster. The requested layout put
  the sidebar control at the main area's lower-left and the model picker at the
  composer's lower-left.
- Finding / root cause: the desktop composer used a single grid row
  (`input model img send`), which forced the picker into the same right-aligned
  control group as image upload and send.
- Changed:
  - `backend/static/index.html` - moved the sidebar-toggle element out of the
    top bar to the main area beside the composer footer; bumped the CSS cache
    version.
  - `backend/static/style.css` - changed desktop composer grid to text row plus
    controls row (`model` left, image/send right), positioned the desktop
    sidebar toggle at main lower-left, and left-aligned the desktop model menu.
- Verified:
  - browser test at 2048x1215 confirmed the model is lower-left of the
    composer, image/send stay lower-right, the model menu is left-anchored, and
    the relocated toggle still collapses the sidebar;
  - browser test at 390x844 confirmed the picker remains in the mobile top bar,
    the mobile toggle stays hidden, the one-line composer remains 52px tall,
    and no horizontal overflow/page errors occur;
  - `node --check backend/static/app.js` and `git diff --check` passed.
- Commit: pending.
- Follow-up / risk: preserve the mobile relocation rule; do not reintroduce the
  desktop two-row composer layout on mobile, where the keyboard requires the
  compact one-line input.

### 2026-08-09 - search conversation message bodies

- Request / symptom: sidebar history search only matched conversation titles;
  users could not find a prior conversation by words that appeared in its
  message body. The visible `Ctrl K` shortcut hint was also unwanted.
- Finding / root cause: `renderList` filtered the already-loaded conversation
  metadata only, and `/api/conversations` intentionally contains no message
  content. Fetching every message into the browser would be wasteful and would
  make search state/races harder to control.
- Changed:
  - `backend/app/db.py` - added owner-scoped title/body search using `EXISTS`
    against `messages`, with literal LIKE escaping for `!`, `%`, and `_`.
  - `backend/app/main.py` - added authenticated
    `GET /api/conversations/search?q=...` before dynamic conversation routes.
  - `backend/static/app.js` - added 180ms-debounced search requests, stale
    response protection, a local title fallback on request failure, and Escape
    reset behavior; removed the Ctrl/Cmd+K search handler.
  - `backend/static/index.html` - removed the visible `Ctrl K` badge and
    bumped the JS cache version.
- Verified:
  - isolated SQLite tests covered title match, message-body match, owner
    isolation, literal percent escaping, and direct authenticated route output;
  - `py_compile` passed for the changed backend modules;
  - browser test intercepted the search endpoint and verified a conversation
    whose title lacked the query appeared from a body-search result, with no
    `kbd` shortcut element, no page errors, and no horizontal overflow;
  - `node --check backend/static/app.js` and `git diff --check` passed.
- Commit: pending.
- Follow-up / risk: body search currently returns matching conversations by
  creation time but not a message excerpt. Add a privacy-reviewed snippet only
  if users need to know which exact message caused a match.

### 2026-08-09 - align desktop sidebar footer with composer controls

- Request / symptom: align the sidebar account row and collapse control with the
  composer send row; align the contact link with the disclaimer; remove the
  outdated sidebar text "fault diagnosis ? independent window per turn".
- Finding / root cause: the sidebar footer and account button were normal flex
  children, so their position was determined by sidebar content rather than the
  composer footer controls. The sidebar toggle used a separate, lower offset.
- Changed:
  - `backend/static/index.html` - removed the obsolete diagnosis text, retained
    the contact link, and bumped the stylesheet cache version.
  - `backend/static/style.css` - on desktop only, anchored the account row and
    collapse control to the send-control centre line and the contact link to
    the disclaimer line. Mobile keeps the normal drawer flow.
- Verified:
  - `git diff --check` and `node --check backend/static/app.js` passed;
  - local server restarted and `GET /` returned HTTP 200;
  - headless browser at 2048x1215 measured account/toggle centres at 1132px
    versus send at 1133.16px, and contact at 1175.5px versus disclaimer at
    1176.58px; the obsolete diagnosis text was absent;
  - headless browser at 390x844 confirmed sidebar account/contact remain
    `position: static` in the mobile drawer.
- Commit: pending (entry written before commit; see git history for final hash).
- Follow-up / risk: desktop offsets intentionally follow the composer baseline.
  If the composer footer height changes, rerun the same geometry check rather
  than manually nudging only one sidebar element.

### 2026-08-09 - rebuild testing tools suite

- Request / symptom: user wanted the deleted test scripts (`_injection_test.py` etc.)
  rebuilt into a proper `tools/` folder, plus a new persona-based progressive
  dialogue test system simulating 3 user levels (beginner/intermediate/advanced)
  with ~20 rounds per scenario including image uploads.
- What was built:
  - `tools/injection_test.py` - rebuilt 12 attack scenarios from report20260808_001
  - `tools/scenarios.py` - 10 progressive dialogue scenarios (4 beginner, 3 intermediate,
    3 advanced) with trigger-based step-by-step disclosure
  - `tools/persona_test.py` - progressive dialogue test engine with quality analysis
  - `tools/run_all.py` - one-click runner (injection + persona)
  - `tools/images/` - 4 AI-generated test images (BSOD, error dialog, device manager,
    task manager)
- Files changed: all new files under `tools/`. No backend code changes.
- Verified: not yet run against live server (needs running FixPilot backend + valid
  invite code or admin credentials).
- Commit: not committed yet.
- Follow-up / risk: persona_test.py currently does not create conversations via API
  first (sends messages without convId, so backend auto-creates). Multi-turn context
  depends on backend storing messages by conversation. The trigger matching is
  keyword-based and may miss some AI reply variations. Image upload uses base64
  encoding in the message body (matching frontend behavior).

### 2026-08-09 - fix image upload + add conv_id to diagnostics logs

- Request / symptom: image upload fails with 400 on Ark Responses API; also need
  diagnostics logs to carry conv_id so AI can trace errors from a conversation URL.
- Finding / root cause: `build_responses_payload` in `llm.py` was missing `type: "message"`
  and `status: "completed"` on user input items. Ark Responses API requires both fields
  on all input items. The error only surfaced when conversation history existed (multi-turn
  with image), because the first turn had no prior messages to validate.
  Separately, `api_diagnostics` logs had no conv_id, and platform API errors (non-custom
  API) were not logged at all.
- Changed:
  - `backend/app/llm.py:216-229` - added `type: "message"` + `status: "completed"` to both
    user and assistant input items in `build_responses_payload`; also fixed the fallback
    empty-input default item.
  - `backend/app/api_diagnostics.py:50` - `start()` now accepts `conv_id` parameter and
    writes it into the log entry.
  - `backend/app/api_diagnostics.py:67` - `success()` now accepts `conv_id`.
  - `backend/app/api_diagnostics.py:97` - `failure()` now accepts `conv_id`.
  - `backend/app/main.py:534` - platform API errors now also create diagnostics entries
    (not just custom API); all `start/success/failure` calls pass `conv_id`.
  - `backend/app/main.py:597-607` - failure messages for platform API show generic text
    (not the provider-specific `public_message` which is only for custom API).
- Verified: `py_compile` passed for llm.py, api_diagnostics.py, main.py. Needs runtime test
  with image upload on Ark Responses API to confirm 400 is gone.
- Commit: not committed yet.
- Follow-up / risk: the `public_message` function is only called for `use_custom_api` now;
  platform API errors show "服务出错，请稍后重试" which is less specific. If users need
  more detail on platform errors, `public_message` could be extended to non-custom cases.
  The `test_chat_connection` function in llm.py still calls `start()` without `conv_id`
  (test requests have no conversation context).

### 2026-08-09 - write fix records back into reports

- Request / symptom: after fixing all bugs and renaming reports with `-fixed`, write the
  fix details back into each report per the new iron rule (per-bug fix section + status
  column + fix date).
- Finding / root cause: two reports needed updates.
- Changed:
  - `reports/report20260808_001-fixed.md` - added fix date; added status column to summary
    table; appended `#### 修复` sections after P1 (llm.py:68) and P3 (llm.py:44); updated
    `## 8. 变更文件` section.
  - `reports/report20260809_001-fixed.md` - added fix date; changed title from "只检不修"
    to plain; added status column to summary table; appended `#### 修复` sections after
    F1-F7; rewrote "交给下一步" from suggestions to executed; updated `## 变更文件` section.
  - `project_memory.md` - added iron rule: fixed reports must contain per-bug fix sections
    (file:line, method, verification), status column, and fix date.
- Verified: both reports re-read to confirm structure matches the new iron rule.
- Commit: not committed yet.
- Follow-up / risk: prompt-level fixes (P1/P3) need runtime regression tests to confirm
  the hallucination and length issues are actually resolved.

### 2026-08-09 - fix all bugs found in reports

- Request / symptom: fix all bugs listed in reports under `reports/`, rename fixed reports
  with `-fixed` suffix, add this naming convention to the iron rules.
- Finding / root cause: two reports contained 9 fixable items total (7 from the layered
  search + 2 prompt-level from the injection test report).
- Changed:
  - `backend/static/app.js` - F1: fixed corrupted comment at line 70.
  - `backend/app/main.py` - F3: added `_require_auth` + ownership check to `/api/title`.
  - `backend/app/knowledge.py` - F4: wrapped `load_chunks()` in try/except, returns `[]` on
    FileNotFoundError or other errors.
  - `backend/app/llm.py` - F6: removed dead `SYSTEM_PROMPT`; P1: added anti-hallucination
    constraint to `LEVEL_POLICIES["unknown"]`; P3: added 250-char limit to SAFETY_POLICY.
  - `backend/app/db.py` - F7: enabled WAL mode in `_connect()`.
  - `backend/static/index.html` - bumped `app.js` cache version to 41.
  - Deleted: `backend/app/fixpilot.db` (F2), `_injection_test.py` / `_test_joke.py` /
    `_mktest.py` (F5).
  - `reports/report20260808_001.md` → renamed to `report20260808_001-fixed.md`.
  - `reports/report20260809_001.md` → renamed to `report20260809_001-fixed.md`.
- Verified:
  - `py_compile` passed for main.py, llm.py, knowledge.py, db.py.
  - `node --check` passed for app.js.
- Commit: not committed yet.
- Follow-up / risk: WAL mode creates `fixpilot.db-wal` and `fixpilot.db-shm` sidecar files;
  ensure they are included in backups. The anti-hallucination constraint in
  `LEVEL_POLICIES["unknown"]` is prompt-based; re-test with injection scenarios to confirm.

### 2026-08-09 - layered bug search (search only, no fixes)

- Request / symptom: run `ai/FixPilot_分层Bug检索与修复流程_v1.1.md` end to end but only
  search, do not fix; archive the report per the project rule (reports/reportYYYYMMDD_NNN.md).
- Finding / root cause: Phase A (10-class matrix) + Phase B (Layer 0-2) found 7 items.
  Confirmed: F1 corrupted comment at `backend/static/app.js:70` (`// ??????????????`);
  F2 duplicate sqlite file `backend/app/fixpilot.db` (in-use path is `backend/fixpilot.db`
  per `db.py:9`); F3 `/api/title` in `backend/app/main.py:445-454` has no `_require_auth`
  and no ownership check, so any client can rename any conversation; F4 module-level
  `_chunks = load_chunks()` in `main.py:31` crashes the app at startup if the transcript
  file is missing (no degrade); F5 leftover debug scripts `_injection_test.py`,
  `_test_joke.py`, `_mktest.py`; F6 dead `SYSTEM_PROMPT` in `llm.py:104` (no callers).
  To-verify (low): F7 SQLite write concurrency across multiple uvicorn workers (single
  process `threading.Lock`, no WAL). No gaps found in injection/XSS/authz-on-other-routes/
  streaming/quota -1.
- Changed:
  - `reports/report20260809_001.md` - added full Phase A + Phase B (Layer 0-2) report.
  - `ai/WORK_LOG.md` - this entry.
- Verified: all findings backed by file:line + code excerpts; cross-checked every route for
  auth, every `json.dumps` for `ensure_ascii=False`, every `open()` for encoding, and the
  frontend risk/profile enums against the backend. No code was modified.
- Commit: not committed yet.
- Follow-up / risk: only F3 (and optionally F4) are worth fixing soon; F1/F2/F5/F6 are
  hygiene. This round intentionally did not fix anything per the user's instruction. If a
  later round is authorized, patch F3 first (mirror `share_conv` authz) and F4 (guard
  `load_chunks`).

### 2026-08-09 - prevent Send clicks from being mistaken for retries

- Request / symptom: clicking Send in a new conversation displayed "return to
  the original conversation to retry" instead of sending the pasted text.
- Finding / root cause: `sendBtn.addEventListener('click', send)` handed the
  browser `MouseEvent` to `send(retryState)`. `Boolean(retryState)` then put a
  normal send into the retry path; the event has no `convId`, so the safety
  guard rejected it.
- Changed:
  - `backend/static/app.js` - discard the click event explicitly and recognise
    retry state only when it contains a non-empty string conversation ID.
  - `AGENTS.md` - added an append-only per-bug `reports/fixed.md` rule that
    complements, not replaces, the task handoff log and batch reports.
  - `reports/fixed.md` - created the individual verified-fix ledger and
    recorded this first event after its regression check passed.
- Verified:
  - headless browser clicked the actual Send button and observed one `/api/chat`
    request with the new conversation ID and typed text, no false retry toast,
    and an enabled Send button after completion;
  - `node --check backend/static/app.js` and `git diff --check` passed.
- Commit: pending (entry written before commit; see git history for final hash).
- Follow-up / risk: keep the retry API object-shaped; do not reintroduce a
  truthiness-only retry check or pass DOM events directly into `send`.

### 2026-08-09 - replace raw admin history dump with private conversation reader

- Request / symptom: the admin history view rendered every user conversation as
  a single raw transcript in the invite-management dialog. It was hard to scan
  and lost the product's normal message hierarchy.
- Finding / root cause: `showHistory` fetched all conversations and concatenated
  title, role label, and escaped content into `ahist-*` text blocks. The public
  share page has better visuals but is token-based and must not be used for
  private admin viewing.
- Changed:
  - `backend/static/app.js` - replaced the raw dump with an authenticated
    conversation list and read-only transcript renderer that reuses normal chat
    bubbles, Markdown rendering, user avatars, memes, images, and timestamps.
  - `backend/static/style.css` - added the private reader's desktop two-pane
    layout and compact mobile horizontal conversation list.
  - `backend/static/index.html` - bumped the app bundle cache version to 43.
- Verified:
  - headless browser loaded two mocked admin conversations, rendered two
    chat-bubble rows with Markdown, showed no legacy role labels, and switched
    to the second conversation correctly;
  - mobile 390px test confirmed the conversation list becomes horizontal;
  - `node --check backend/static/app.js`, `git diff --check`, and local `GET /`
    HTTP 200 passed.
- Commit: pending (entry written before commit; see git history for final hash).
- Follow-up / risk: the existing admin endpoint still returns all messages for
  an invite at once. Keep it for the current small-scale product; paginate or
  add per-conversation retrieval if invite histories become large.

### 2026-08-09 - persona test run + fix AI refusing images

- Request / symptom: run full persona-based progressive dialogue tests (3
  personas x 3 scenarios = 9 scenarios), record bugs found to
  `reports/report20260809_002.md`, fix and continue. User clarified that
  `scenarios.py` must store complete fault truth (symptoms, hardware, timeline,
  outcomes, images, grading), NOT predicted dialogue scripts; the tutor AI
  dynamically responds based on facts + persona style.
- Finding / root cause:
  - Confirmed `scenarios.py` already stores complete fault truth (facts +
    grading), not dialogue scripts. Persona only affects the tutor AI's
    expression style, not the facts.
  - Ran 9 scenarios (71 rounds total): 8/9 solved, 9/9 correct diagnosis
    direction. Found 3 bugs + 1 test coverage gap:
    - P1 (I03 R11): HTTP 500 empty reply when user asked about DEP settings
      (conv_id: c72dd6831137cedd4). Likely DeepSeek API timeout/limit on long
      context. NOT fixed.
    - P2 (A03 R2 + A02 R6): AI proactively tells users "别发图，我看不了图"
      and "我这边看不到截图". Root cause: `llm.py:13` BASE_POLICY said
      "不能真正看图", AI interpreted as "cannot process any images" and
      refused images, despite having OCR pipeline. FIXED.
    - P3: test coverage gap - tutor AI (deepseek-chat) never output [IMG:path]
      tags in 71 rounds, so OCR pipeline was not tested at all.
- Changed:
  - `backend/app/llm.py:13` - rewrote BASE_POLICY boundary line: "能识别用户
    上传截图中的文字（如蓝屏代码、错误对话框、设备管理器状态、任务管理器
    数值）；用户发来截图时应鼓励，不要说'看不了图'或拒绝接收。但不能'看图'
    判断硬件外观、接线是否正确、屏幕画面等需要视觉判断的内容..."
  - `reports/report20260809_002.md` - created full test report with 3 bugs +
    1 coverage gap, speed table, per-scenario details, P2 fix section.
  - `reports/fixed.md` - appended P2 fix entry per the per-bug ledger rule.
- Verified:
  - `py_compile` passed for `llm.py`.
  - Backend uvicorn restarted successfully (old PID 60580 stopped, new PID
    59824 running on port 8000).
  - Health endpoint returns `{"status":"ok","chunks":80}`.
  - Test results saved to `tools/persona_results.json`.
- Commit: not committed yet.
- Follow-up / risk:
  - P1 (HTTP 500) needs investigation: check `backend/logs/api-diagnostics.log`
    for conv_id `c72dd6831137cedd4` to find the exact error. May need retry
    logic or context truncation for long conversations.
  - P2 fix needs verification: re-run A03 scenario to confirm AI no longer
    says "看不了图".
  - P3 coverage gap: improve `persona_test.py` tutor AI prompt to force image
    sending when FixPilot asks for screenshots, or add `must_send_round` field
    to scenarios.
  - The report is NOT renamed to `-fixed` because P1 and P3 are still open.

### 2026-08-09 - take over persona-test framework and validate the first fixes

- Request / symptom: audit and take over `ai/HANDOFF_persona_test.md`, then turn its P1/P2/P3 claims into verified, maintainable test behavior.
- Finding / root cause:
  - P1 was not HTTP 500. The provider sometimes ended a successful SSE request with reasoning-only deltas and no displayable `content`; the test tool incorrectly converted the SSE application error into status 500.
  - P2's prompt change existed but had only compile-time verification.
  - P3 was real: optional tutor `[IMG:...]` markers left all configured OCR images untested.
  - The original direction grader also had a false-positive defect: generic words such as an error code or "administrator" could mark a wrong diagnosis as correct.
  - The local service initially could not use an inherited SOCKS proxy because `socksio` was absent from runtime dependencies.
- Changed:
  - `backend/app/llm.py` - added a safe Chat Completions non-streaming fallback after an empty stream; retained the existing screenshot-text policy; added a completed-response text extractor.
  - `backend/requirements.txt` - declared `socksio` for inherited SOCKS proxy support.
  - `tools/persona_test.py` - records SSE application failures separately, forces due scenario images, and grades direction through discriminative evidence groups.
  - `tools/scenarios.py` - added per-image trigger/due metadata and per-scenario direction-evidence groups.
  - `reports/report20260809_002.md` and `reports/fixed.md` - recorded the corrected findings and targeted verification state.
- Verified:
  - no-network mocked tests covered empty-stream-to-completed fallback, no duplicate retry after visible text, Responses output extraction, SSE error classification, deterministic image delivery, and direction-grading false positives;
  - `py_compile` passed for updated backend and test modules; `git diff --check` passed;
  - local server restarted successfully and `/api/health` returned 200;
  - targeted A03 sent a real OCR image on round 2 and completed in 8 rounds with no image rejection or response failure;
  - targeted I03 completed 14 rounds with no stream/HTTP/empty-reply failure; regrading proves its diagnosis branch was actually wrong, so the full report must be rebaselined rather than called 9/9 correct.
- Commit: `committed atomically with this implementation; inspect Git history for the final hash`; unrelated prior uncommitted work remains intentionally unstaged.
- Follow-up / risk: run all 9 scenarios with the tightened grader before renaming the report `-fixed`. I03's content-quality regression (wrong branch after runtime-library checks) is now visible and needs product/prompt work; do not hide it behind the P1 transport fix.

### 2026-08-09 - modularize the product test workflow and preserve design context

- Request / symptom: turn the dynamic persona-test handoff into a dependable, reusable testing process; make “我要测试” meaningful to later AI agents; retain the useful Trae product conversation in the repository.
- Finding / root cause:
  - the original tools duplicated authentication/SSE behavior and did not give the orchestration layer a consistent ERROR/REVIEW result model;
  - persona tests could visually simulate a user level without proving the backend had received that level;
  - safety behavior had no focused live-regression suite;
  - durable context existed only in an external share link and a one-off handoff.
- Changed:
  - AGENTS.md - added the repository test-workflow trigger and mandatory reading order for future agents.
  - ai/Testing/ - added the workflow, FixPilot-specific test profile, and new-project template.
  - ai/Chats/ - added a sanitised archive convention and the Trae dynamic-persona-test decision record.
  - tools/testkit.py - centralized authentication, profile setup verification, conversation creation, image payload creation, SSE parsing, and failure classification.
  - tools/persona_test.py - uses the shared transport and supports explicit/unknown backend profile modes plus an independent response-style override.
  - tools/injection_test.py - shares transport semantics so an error cannot be counted as a defended attack.
  - tools/safety_test.py - added FixPilot-specific medium/high risk notice and stop-guidance regression cases.
  - tools/run_all.py - added modular suite selection, independent style selection, structured summaries, non-zero exit for FAIL/ERROR/REVIEW, and default local result artifacts.
  - .gitignore - excludes generated local test result JSON.
- Verified:
  - Python compilation passed for every changed test module;
  - the run_all and persona_test command help expose suite selection, profile mode, and response-style override;
  - no-network mocked checks passed for numbered-option parsing, request/SSE classification, risk PASS/FAIL/REVIEW classification, and explicit/unknown persona profile setup;
  - git diff --check passed, the local health endpoint returned status ok, and the new test modules contain no literal question-mark corruption.
  - the live tutor/full-product suite was deliberately not run: it would consume external model quota and needs a chosen local account; no live-product PASS is claimed.
- Commit: pending.
- Follow-up / risk:
  - rerun all nine persona scenarios with the tightened evidence grading before declaring the historic full-suite score current;
  - UI regressions remain browser/manual checks until a stable browser suite is added;
  - for a different project, copy the playbook/template and write that project’s own truth fixtures rather than copying FixPilot’s scenarios.



### 2026-08-09 - standardize internal A/B/C test cohorts

- Request / symptom: replace vague internal cohort labels and mixed B/I/A scenario IDs with one stable A/B/C convention. The user explicitly clarified that these letters are for team/test use only and must never be shown to product users.
- Finding / root cause: the test scenarios used three overlapping vocabularies: backend enum values (`beginner` / `intermediate` / `advanced`), colloquial team labels, and B/I/A IDs. This made reports and regression commands ambiguous.
- Changed:
  - `tools/scenarios.py` - made the test cohort keys and IDs consistent: A = advanced/direct technical discussion, B = intermediate/can tinker, C = beginner/detailed guidance. Existing runtime enum values remain unchanged.
  - `tools/persona_test.py` and `tools/run_all.py` - accept `--persona A|B|C`; examples use the new IDs.
  - `ai/Testing/FixPilot_TEST_PROFILE.md` - documents the mapping and the rule that A/B/C cannot appear in user-facing UI or assistant copy.
  - `reports/fixed.md` - records the brief reversed-mapping correction made during this uncommitted refactor.
  - `ai/RELEASE_READINESS.md` - records the evidence-based beta/public-launch gate as of this audit.
- Verified:
  - `python -m py_compile tools/scenarios.py tools/persona_test.py tools/run_all.py` passed.
  - A no-network assertion verified A -> `advanced`, B -> `intermediate`, C -> `beginner`, and IDs C01-C03 / B01-B03 / A01-A03 point to those cohorts.
  - Both CLI help screens expose only `--persona {A,B,C}`; `git diff --check` passed after the documentation encoding repair.
- Commit: pending.
- Follow-up / risk: historical reports and chat archives intentionally retain their old wording because they describe past runs. Do not rename the persisted backend values without a migration; they are API/storage data, not the internal test vocabulary.

## Append template

Copy this section for every new task; append it above this template.

```md
### YYYY-MM-DD - short task title

- Request / symptom:
- Finding / root cause:
- Changed:
  - `path/to/file` - what changed
- Verified:
  - command or browser scenario and result
- Commit: `abc1234 subject` (or `not committed yet`)
- Follow-up / risk:
```


### 2026-08-09 - repair response rendering integrity and harden administrator boundary

- Request / symptom:
  - Two live conversations rendered ordinary answers incorrectly: Chinese text was stretched across a bubble, normal numbered text was split into controls, and unmatched Markdown fences could hide a reply tail.
  - A blue-screen screenshot conversation incorrectly claimed that screenshots could not be read, despite the OCR path.
  - The user requested a hard administrator/instruction-injection boundary after seeing untrusted content near the admin experience.
- Finding / root cause:
  - `text-align: justify` stretched short Chinese lines; the same rule existed in share-page bubbles.
  - The frontend used heuristic numbered-list detection and `breakNumbered()` to mutate model output before rendering. This could reclassify procedural steps as selectable cards and split original text. An unmatched triple-backtick fence also turned the remainder into a code block.
  - The prompt did not distinguish supported OCR screenshot text strongly enough from unsupported physical visual inspection.
  - `/api/chat` trusted client-supplied message roles, so a direct caller could attempt to inject a `system` or forged `assistant` message into model context. The project also had a fallback default administrator credential in source/example configuration.
- Changed:
  - `backend/static/style.css` - changed bot/share bubble alignment to left alignment.
  - `backend/static/app.js` - only explicit `选项：` blocks can render as clickable options; removed source-mutating numbered-step rewriting; renders unmatched fences as visible text; replaces corrupt question-mark-only conversation titles with `未命名对话`.
  - `backend/app/llm.py` - makes OCR support for blue-screen/error screenshots explicit and adds an untrusted-input/prompt-injection rule.
  - `backend/app/service.py` and `backend/app/main.py` - accept exactly one current `user` message from a chat request, keep history server-owned, whitelist stored history roles, and prevent invite accounts from claiming an administrator name.
  - `backend/app/auth.py`, `backend/app/config.py`, and `backend/.env.example` - remove default admin bootstrap credentials and add an in-memory five-failure/ten-minute administrator login guard.
  - `reports/fixed.md` - added per-event fixed records for this task.
- Verified:
  - Node assertions: ordinary numbered steps remain text; only strict `选项：` syntax becomes choices; unmatched code fences keep the tail visible.
  - Python assertions: invalid client `system`/`assistant` roles and malformed message lists are rejected; history role filtering works; missing admin environment credentials create no admin; login failure throttling engages and resets correctly.
  - Direct live-route assertion: `/api/chat` rejects forged `system` and `assistant` roles with HTTP 400 before creating a conversation or invoking a provider.
  - `python -m py_compile backend\app\auth.py backend\app\config.py backend\app\llm.py backend\app\main.py backend\app\service.py`, `git diff --check`, and restarted local `/api/health` all passed. Served `app.js` and `style.css` contain the renderer fix.
- Commit: `70441ec fix: preserve reply text and harden admin boundary`.
- Follow-up / risk:
  - Existing stored model text is not rewritten because reconstructing it could alter evidence; refresh the affected conversations to see the layout correction, then resend if a historical response itself was already malformed.
  - Browser-plugin initialization failed before page inspection in this environment, so a final manual visual refresh is still needed for the two supplied URLs.

### 2026-08-09 - automate answer-rendering regression coverage

- Request / symptom: the user clarified that regression verification for a later, lower-cost AI must use the repository's existing automated tools rather than depend on a manually written chat script. Recent P1 incidents included stretched Chinese text, normal numbered instructions being turned into option cards, and an unmatched Markdown fence hiding part of a reply.
- Finding / root cause: the existing `tools/run_all.py` covered injection, safety, and persona conversations, but it had no no-cost suite that exercised the frontend answer-rendering rules. A later tester could therefore run API checks without noticing visual/content-parser regressions.
- Changed:
  - `tools/renderer_test.js` - added five DOM-free checks against the real frontend renderer source: numbered procedures stay text, only an explicit `选项：` marker creates cards, unmatched fences cannot hide reply tails, question-mark-only titles fall back safely, and main/share assistant bubbles are left aligned.
  - `tools/run_all.py` - registered `renderer` as a first-class suite, made it runnable without credentials/model calls, and retained credential requirements for API-backed suites only.
  - `ai/Testing/FixPilot_TEST_PROFILE.md` and `ai/Testing/README.md` - documented the renderer suite and the zero-cost command.
- Verified:
  - `node tools/renderer_test.js` - R01-R05 all PASS.
  - `python -m py_compile tools/run_all.py` - PASS.
  - `python tools/run_all.py --suites renderer` - PASS 5 / FAIL 0 / ERROR 0 / REVIEW 0; local JSON evidence written under ignored `reports/test-runs/`.
  - `python tools/run_all.py --help` exposes `renderer` and `--skip-renderer`; `git diff --check` passed.
- Commit: 4707da5 (`test: automate answer renderer regressions`).
- Follow-up / risk: this suite protects parser/layout invariants but is not a replacement for browser checks at desktop and mobile breakpoints. If the browser automation runtime is available, pair relevant UI changes with responsive visual checks.
### 2026-08-09 - update direct DeepSeek settings for official V4 Flash

- Request / symptom: the user asked whether the newly released official DeepSeek V4 Flash required a new integration path. The direct DeepSeek API settings still suggested the retired `deepseek-chat` model alias.
- Finding / root cause: the runtime default was already `deepseek-v4-flash`, and the backend already supports both Chat Completions and an explicit `/responses` endpoint. Only the frontend direct-DeepSeek preset and its visible model placeholder were stale.
- Changed:
  - `backend/static/app.js` - changed the direct DeepSeek preset model to `deepseek-v4-flash`.
  - `backend/static/index.html` - changed the model placeholder and bumped the app JavaScript cache version from 43 to 44.
  - `reports/fixed.md` - added the required individual bug-fix ledger entry.
- Verified:
  - `node --check backend/static/app.js` passed.
  - static assertions confirmed no retired alias remains in the direct preset, the new placeholder and cache version are present.
  - an offline Python assertion confirmed `https://api.deepseek.com/responses` is translated to a valid `deepseek-v4-flash` Responses request with `instructions` and typed `input_text` content.
  - `git diff --check` passed.
- Commit: 4d88cd3 (`fix: use official DeepSeek V4 Flash preset`).
- Follow-up / risk: Chat Completions remains the recommended default because it retains visible streaming. Users may still configure `https://api.deepseek.com/responses` manually; FixPilot currently retrieves that upstream result non-streaming for stability, so it does not expose the provider's native token-by-token events.

### 2026-08-09 - close risk-notice and empty-reply regressions from report 003

- Request / symptom:
  - `reports/report20260809_003.md` identified S03 missing a high-risk BIOS notice, S04 missing a medium-risk driver-operation notice, and A02 failing after an empty stream plus empty fallback.
- Finding / root cause:
  - Trusted risk cards depended only on model-emitted markers, so a model omission bypassed the UI even where the policy requested a marker.
  - The BIOS rule did not explicitly encompass changing BIOS/UEFI settings, and the driver fallback did not cover common Chinese “卸掉再装” phrasing.
  - After no user-visible streamed content and an empty completed fallback, the transport stopped instead of attempting one safe retry.
- Changed:
  - `backend/app/safety.py` - added conservative direct-operation risk inference for BIOS/UEFI changes, high-risk data/firmware/power actions, and driver remove/reinstall actions.
  - `backend/app/main.py` - emits the trusted risk notice before the model reply when the direct user request is unambiguous; avoids duplicate notice emission when the model also marks it.
  - `backend/app/llm.py` - clarifies BIOS/driver classification and retries one completed request only when no displayable text has ever been streamed.
  - `tools/transport_test.py` - added no-network regression assertions for both risk preflight tiers and safe empty-reply retry behavior.
  - `tools/run_all.py`, `ai/Testing/README.md`, `ai/Testing/FixPilot_TEST_PROFILE.md` - registered and documented the credential-free `transport` suite.
  - `reports/fixed.md` - added the mandatory individual fixed-event entries.
- Verified:
  - Live local authenticated safety suite: S01-S04 PASS, including the former S03/S04 failures.
  - `python -m py_compile backend\\app\\safety.py backend\\app\\llm.py backend\\app\\main.py tools\\transport_test.py tools\\run_all.py` - PASS.
  - `python tools\\transport_test.py` - T01-T03 PASS.
  - `python tools\\run_all.py --suites renderer,transport` - renderer PASS 5; transport PASS 3.
  - `git diff --check` - PASS.
  - A targeted live A02 persona run was attempted, but the desktop command host terminated the detached process before a result artifact. It is explicitly not recorded as a passing live regression.
- Commit: pending.
- Follow-up / risk:
  - The preflight is intentionally conservative and only recognizes direct named operations; model markers are still needed for risks that appear later in a reply rather than in the user's request.
  - A provider that returns empty text twice will still show the existing error state; silently fabricating an answer would be worse.

#### Commit reference - 2026-08-09

The work item immediately above was implemented and verified in `a2b4b16` (`fix: harden risk notices and empty replies`).

### 2026-08-09 - store per-account custom API settings on the server

- Request / symptom: the user's custom API configuration (key/base/model) was
  saved only in the browser `localStorage`, so it did not follow the account
  and could not be shared across devices. The user asked to store it on our
  server, keyed per account, where an invite-code-only user and the same
  invite's bound username share one configuration. Also, the admin
  invite-management panel should show the bound username next to the invite
  code, separated by a `|`.
- Finding / root cause:
  - API settings lived under `fixpilot_api_settings` in `localStorage`
    (`app.js`). There was no server-side persistence and no per-user key.
  - Invite codes and users are already bound one-to-one via
    `users.invite_code`, and profiles are already stored per `owner_key`
    (invite code for users, `admin:<username>` for admins). The same
    `owner_key` granularity is the correct key for API settings, so an invite
    user and its bound account share one configuration as requested.
- Changed:
  - `backend/app/db.py` - added `user_api_settings` table keyed by
    `owner_key`; added `get_api_settings` / `save_api_settings` (upsert) /
    `clear_api_settings`; changed `list_invites` to LEFT JOIN `users` and
    return `bound_username`.
  - `backend/app/main.py` - added `GET /api/api-settings`,
    `POST /api/api-settings`, and `POST /api/api-settings/clear`, all
    authenticated and scoped to `_owner(payload)`.
  - `backend/static/app.js` - replaced the localStorage-backed API settings
    with an in-memory cache loaded from the server on login
    (`loadApiSettingsFromServer` called in `enterApp`); `saveApiSettings` /
    `clearApiSettings` now persist to the server in the background while
    updating the cache synchronously; removed the now-unused
    `API_SETTINGS_KEY`; the admin invite table now renders
    `CODE | username` when a bound username exists.
- Verified:
  - `python -m py_compile backend/app/db.py backend/app/main.py` PASS.
  - `node --check backend/static/app.js` PASS.
  - Live HTTP flow (admin token): `GET /api/api-settings` returns default
    `platform`/empty key; `POST /api/api-settings` returns `ok`; re-GET returns
    the saved custom config; `POST /api/api-settings/clear` then re-GET returns
    the default again. `GET /api/admin/invites` returns `bound_username` for
    the bound code (e.g. `4CDB97` -> `test123`) and `None` for unbounded ones.
  - Browser smoke (admin login): login succeeds, no console errors
    (including api-settings/fetch/localStorage).
  - A deadlock was found and fixed during verification: `save_api_settings`
    called `get_api_settings` while holding the non-reentrant DB `_lock`,
    hanging every save. It now returns a constructed dict instead. This is
    recorded in `reports/fixed.md`.
- Additional verification before commit: isolated temporary SQLite database test confirmed default values, save/reload, and clear/reset behavior without using a real API key.
- Implementation commit: ad6c48f3eea7a988935ff88041ebc98cf33df478 (`feat: persist custom API settings and testing records`).
- Follow-up / risk:
  - The backend must be restarted to load the new schema and endpoints.
  - Accepting the API key in an authenticated `GET /api/api-settings`
    response is intentional (the frontend needs it to issue chat requests);
    it is transmitted only over the authenticated channel and never logged.
  - Existing custom API settings stored in the browser before this change are
    not migrated; the user re-enters them once after login.

### 2026-08-09 - add explicit official DeepSeek V4 Flash web-search turns

- Request / behavior: users need a way to deliberately look up current public
  material while troubleshooting, without making ordinary chats or every custom
  API call silently networked.
- Finding / design decision: DeepSeek's official Responses API supports the
  server-side `web_search` tool for `deepseek-v4-flash`. The existing app had a
  Responses adapter but deliberately disabled tools, so it could not perform a
  controlled search turn.
- Changed:
  - `backend/app/llm.py` - added a strict host/model gate
    (`api.deepseek.com` + exact `deepseek-v4-flash`), forces approved search
    calls to the official `/responses` endpoint with `web_search`, preserves
    only provider-returned HTTP(S) source URLs, and adds a trusted visible
    search label.
  - `backend/app/service.py` and `backend/app/main.py` - pass the one-turn
    `webSearch` flag through prompt assembly and transport; the search policy
    treats web pages as untrusted external material and preserves safety/RAG
    precedence.
  - `backend/static/index.html`, `backend/static/style.css`, and
    `backend/static/app.js` - added the one-turn `查资料` control. It resets
    after sending, stays with a failed-message retry, and is disabled when the
    active model is not the supported official Flash configuration.
  - `tools/web_search_test.py`, `tools/run_all.py`, `ai/Testing/README.md`, and
    `ai/FixPilot_联网资料检索规范_v1.0.md` - added a credential-free test module,
    runner registration, policy, and handoff instructions.
- Additional safeguard: the browser now follows the server-reported platform capability. A platform model named Flash does not expose search unless its configured endpoint is actually official `api.deepseek.com`; custom API use still requires the same host/model gate.
- Verified:
  - `python tools/run_all.py --suites renderer,transport,websearch` passed:
    renderer 5, transport 3, websearch 5.
  - Python compilation passed for changed backend/test modules; `node --check
    backend/static/app.js` and `git diff --check` passed.
  - A live official DeepSeek V4 Flash search call completed through
    `/responses`, returned a non-empty answer, and included a provider-returned
    source URL. No credentials were printed or recorded.
  - Local server restarted successfully; `/api/health` returned OK and the
    OpenAPI schema exposes `ChatRequest.webSearch`.
  - The in-app browser control could not initialize because its local kernel
    assets path is unavailable, so visual desktop/mobile clicking remains a
    manual follow-up despite static and regression checks passing.
- Implementation commit: 5cb461163b0290aa12f8948a8d8f131ff1966062 (`feat: add official DeepSeek web search`).
- Follow-up / risk: this is intentionally a narrow v1. Do not add web search
  to Fire/Volcengine/custom endpoints without provider-specific evidence,
  source parsing tests, and a separate product decision. Recheck desktop and
  390px mobile layout manually after a cache refresh.


### 2026-08-09 - reserve the sidebar footer and keep external lookup optional

- Request / symptom: the desktop conversation list could render beneath the fixed account/contact area (including the admin row). The user also required the one-turn `???` control to supplement manuals/PDFs/model-specific documentation without turning normal FixPilot diagnosis into generic web search.
- Finding / root cause: desktop CSS absolutely positioned the account and contact controls while `.conv-list` was allowed to consume the entire sidebar height. The official DeepSeek search payload used `tool_choice`, forcing a web-search call every time the user clicked the one-turn control.
- Changed:
  - `backend/static/index.html` and `backend/static/style.css` - moved the account/contact block into the sidebar flex layout, added a visible boundary, and constrained the conversation scroller with `min-height: 0`; the list now reserves space instead of drawing behind the footer.
  - `backend/app/llm.py` - changed the web-search instruction from mandatory search to conditional external evidence; the payload now exposes `web_search` but does not force `tool_choice`; the visible search label is emitted only when provider output proves a search tool call occurred.
  - `backend/static/app.js` and `backend/static/index.html` - clarified the one-turn control tooltip: it is for model, manual, PDF, official driver, and compatibility material.
  - `tools/web_search_test.py` - added a regression case proving the search capability remains optional and an unneeded request is labelled as not externally searched.
  - `ai/FixPilot_????????_v1.0.md` - revised the product rule to match the optional-search behavior and the knowledge-base-first boundary.
- Verified: `python -m py_compile backend/app/llm.py tools/web_search_test.py` PASS; `node --check backend/static/app.js` PASS; `python tools/run_all.py --suites renderer,transport,websearch` PASS (renderer 5, transport 3, websearch 6); `git diff --check` PASS.
- Commit: pending.
- Follow-up / risk: automated browser visual control is unavailable in this environment, so confirm the desktop sidebar at a long-history account and 390px mobile manually after the server restart. The model still decides whether a permitted lookup is necessary; the regression tests cover request construction and transparent labelling, not a paid live provider call.


#### Commit reference - 2026-08-09 Asia/Shanghai

The optional external-lookup behavior and sidebar boundary fix above were implemented and verified in commit `3a37a8b` (`fix: keep lookup optional and reserve sidebar footer`).


### 2026-08-09 - make official-reference lookup server-decided and knowledge-base-first

- Request / product correction: remove the visible `???` control. The user wants FixPilot itself to decide whether official material is necessary, while routine diagnosis remains conservative and driven by the local knowledge base.
- Finding / root cause: the first implementation represented lookup as a browser toggle and a client-supplied `webSearch` request field. Even after removing forced `tool_choice`, that UI still asked users to make a product-level evidence decision and made the feature appear like general-purpose search.
- Changed:
  - `backend/static/index.html`, `backend/static/style.css`, and `backend/static/app.js` - removed the user switch, state, retry flag, capability plumbing, and its composer grid slot; the model picker, image button, and send button close the resulting space.
  - `backend/app/main.py` - removed the public `webSearch` request field and the now-unused capability response field. A client cannot turn lookup on.
  - `backend/app/service.py` and `backend/app/llm.py` - the server grants tool availability only for the exact official `api.deepseek.com` + `deepseek-v4-flash` path. The model receives a knowledge-base-first, official-sources-only rule and decides whether to call the optional tool; no `tool_choice` is sent. Ordinary answers remain unlabelled; only an actual tool call receives an external-source disclosure and provider URLs.
  - `tools/web_search_test.py` - replaced the one-turn-control checks with server-decision, official-provider gate, actual-source, no-banner, and no-user-control regression coverage.
  - `ai/FixPilot_????????_v1.0.md`, `ai/FixPilot??????.md`, `ai/FixPilot_?????????_v1.0.md`, `ai/FixPilot_Prompt??????????_v1.0.md`, and `ai/Testing/README.md` - aligned handoff, capability, persona, and test documentation with the new narrow policy.
- Verified: `python -m py_compile backend/app/llm.py backend/app/service.py backend/app/main.py tools/web_search_test.py` PASS; `node --check backend/static/app.js` PASS; `python tools/run_all.py --suites renderer,transport,websearch` PASS (renderer 5, transport 3, websearch 7); source contract confirms the browser and chat API contain no `webSearch` control/field; `git diff --check` PASS. No paid/live provider call was made.
- Commit: pending.
- Follow-up / risk: the LLM controls whether to call the enabled tool. The policy limits it to official references, but a live provider acceptance check with a concrete model/manual question is still useful before broad release; do not count an unverified external page as a confirmed diagnosis.

#### Commit reference - 2026-08-09 Asia/Shanghai

The automatic, official-reference-only lookup policy above was implemented and verified in commit `0879ba7` (`feat: make official lookup automatic`).


### 2026-08-09 - audit and enforce the official-source registry

- Request / goal: take over the new `data/official_sources.json` catalogue, audit it instead of trusting a cheap-agent research result blindly, and make external lookup conservative: local knowledge base first, official material only when the current turn actually needs it.
- Finding / root cause: the file was a useful candidate list but was not used at runtime. Its metadata was inconsistent with the records; one pending Colorful entry was enabled; several configured URLs had moved, redirected to unregistered official hosts, returned 404, or were not stably reachable. The provider web-search integration does not expose a documented server-side domain-filter option, so an instruction alone could not enforce the intended source boundary.
- Changed:
  - `data/official_sources.json` - normalized the v1 runtime schema; corrected metadata; refreshed Microsoft, Intel, Honor, and TP-Link entry points/hosts; added identifier, risk, target-confirmation, source-tier, and vendor-alias metadata; retained only 23 reachable verified official records as enabled. The other 17 records, including all nonofficial archives, are preserved but disabled for review.
  - `backend/app/official_sources.py` - added conservative registry selection: no vendor plus identifiable model/identifier means no external tool. It also provides strict hostname allowlist matching and a per-turn source policy.
  - `backend/app/service.py` and `backend/app/llm.py` - require both the official DeepSeek V4 Flash provider and a registry match before enabling `web_search`; pass only matching manufacturer domains to the response filter; refuse to display an unapproved provider URL or its external conclusion as FixPilot evidence.
  - `tools/official_sources_test.py`, `tools/official_sources_audit.py`, `tools/run_all.py`, and `tools/web_search_test.py` - added deterministic registry regression coverage, a separate live read-only audit, runner integration, and transport tests for generic-symptom denial, vendor-scoped routing, and lookalike-domain rejection.
  - `ai/FixPilot_Official_Source_Registry_v1.0.md`, `ai/FixPilot_????????_v1.0.md`, `ai/Testing/README.md`, and `reports/official-source-audit-20260809.md` - documented the runtime contract, maintenance procedure, provider limitation, and live audit evidence.
- Verified: `python -m py_compile backend/app/official_sources.py backend/app/llm.py backend/app/service.py tools/official_sources_test.py tools/official_sources_audit.py tools/web_search_test.py` PASS; `node --check backend/static/app.js` PASS; `python tools/run_all.py --suites renderer,transport,websearch,sources` PASS (renderer 5, transport 3, websearch 8, sources 6); `python tools/official_sources_audit.py --enabled-only` PASS (23 reachable, 0 review); `git diff --check` PASS. No paid/live model request was made.
- Commit: pending.
- Follow-up / risk: the provider's tool cannot yet be hard-restricted by a documented domain parameter. The registry therefore uses provider gating, per-turn source policy, and URL output filtering; a future direct official-site fetcher would make the transport boundary stronger. Disabled candidates must be manually rechecked before enabling.

#### Commit reference - 2026-08-09 Asia/Shanghai

The official-source registry audit and runtime lookup gate above were implemented and verified in commit `cc47baf` (`feat: gate lookup with official source registry`).


### 2026-08-09 - change the official-source registry from a hard allowlist to a preferred route

- Request / product correction: the user clarified that the curated source directory must be a fast, high-trust first route, not a restriction that prevents FixPilot from finding a missing vendor's official manual or other official documentation.
- Finding / root cause: the prior runtime gate required a registry match and then removed every provider-returned URL outside that turn's selected domains. A real unlisted official source was therefore treated the same as a forum result, and its answer was replaced by a rejection message.
- Changed:
  - `backend/app/official_sources.py` - added a narrowly scoped eligibility path for an identifiable model plus explicit documentation intent (manual, driver, firmware, BIOS/UEFI, specification, or compatibility). Generic symptom-only chat remains in the local knowledge-base path.
  - `backend/app/service.py` and `backend/app/llm.py` - renamed the domain transport field to `preferred_source_domains`; preferred registry domains are tried first, while a direct official manufacturer/OS/hardware source may be used only when the preferred route lacks the material. Returned registry links are labelled `??????`; other returned links are labelled `?????????????` with a cross-check warning. High-risk actions still require the normal source ownership, exact-target, and risk confirmation rules.
  - `tools/web_search_test.py` and `tools/official_sources_test.py` - added regression coverage for generic-symptom denial, concrete unlisted documentation requests, preferred-source labelling, and unlisted-source downgrading.
  - `ai/FixPilot_Official_Source_Registry_v1.0.md`, `ai/FixPilot_????????_v1.0.md`, and `ai/Testing/README.md` - updated the contract and maintenance guidance so later agents do not restore a hard domain wall.
- Verified: `python -m py_compile backend/app/official_sources.py backend/app/llm.py backend/app/service.py tools/official_sources_test.py tools/web_search_test.py` PASS; `python tools/run_all.py --suites renderer,transport,websearch,sources` PASS (renderer 5, transport 3, websearch 9, sources 7); `git diff --check` PASS. No live or paid provider request was made.
- Implementation commit: `8d472be` (`fix: prioritize official source registry`).
- Follow-up / risk: the provider web-search tool still lacks a documented server-side domain-preference parameter. Prompt policy plus visible labels guide the result, but cannot prove an arbitrary returned page is official. For firmware, BIOS, data, partition, or hardware-risk work, treat an unlisted result only as a lead and verify source ownership plus exact model before proceeding.


### 2026-08-09 - keep the official-only fallback policy when no preferred registry entry exists

- Request / follow-up: after changing the source directory into a preferred route, ensure that a concrete unlisted documentation request does not reach the model with an empty per-turn source policy.
- Finding / root cause: `build_lookup_policy([])` returned an empty string. The global official-reference rule still existed, but the model did not receive the explicit unlisted-request boundary that says to broaden only to a direct manufacturer, operating-system, or hardware-vendor official page.
- Changed: `backend/app/official_sources.py` now emits that explicit fallback policy whenever no curated route matches. `tools/web_search_test.py` asserts the policy is present for an unlisted model-plus-documentation request.
- Verified: `python -m py_compile backend/app/official_sources.py tools/web_search_test.py` PASS; `python tools/run_all.py --suites websearch,sources` PASS (websearch 9, sources 7); `git diff --check` PASS.
- Implementation commit: `c95a900` (`fix: retain official fallback policy`).
- Follow-up / risk: source ownership and exact-model applicability still cannot be proved solely by the provider search tool; high-risk controls remain mandatory.

### 2026-08-10 - restrict password fields to printable ASCII (no Chinese)

- Request / problem: after the length guard was added, the user still could type Chinese characters into a password field ("为什么密码还是可以输入汉字"). The audit covered length only, not character type.
- Finding / root cause: the previous fix added `maxlength` (length) but no character-type restriction, so Chinese/emoji/full-width chars were still accepted. The user wants password/secret fields to accept only keyboard-printable ASCII.
- Changed:
  - backend/static/app.js - added a delegated `input` listener that strips any non-printable-ASCII (`[^\x20-\x7e]`) from every `type="password"` field in real time (covers static login + dynamically rendered bind/change-password fields, and the API key field).
  - backend/app/main.py - bind-account and change-password now reject passwords not matching `[\x20-\x7e]+` ("密码不能包含汉字等非键盘字符"); moved `import re` to module top.
- Verified: `python -m py_compile backend/app/main.py` PASS; `node --check backend/static/app.js` PASS.
- Implementation commit: none (per project rule, commit/push only on explicit user instruction).
- Follow-up / risk: existing stored passwords are unaffected (filtering only applies to new input; login verifies the stored hash). Frontend filter is a UX guard; backend regex is the hard enforcement.

### 2026-08-10 - add input length/type guards across the whole project

- Request / problem: user found they could paste several thousand Chinese characters into a password field. Asked for a project-wide audit of input length and type limits.
- Finding / root cause: every input only enforced a lower bound (e.g. password >= 6) with no upper limit, and almost no frontend maxlength. Backend endpoints likewise only checked lower bounds, so oversized values (huge passwords slowing PBKDF2, oversized notes, oversized chat text) were accepted.
- Changed:
  - backend/app/main.py - added `_MAX_PASSWORD_LEN=64`, `_MAX_USERNAME_LEN=64`; reject oversized credentials before PBKDF2 in admin-login/account-login; 6-64 password bounds in bind-account/change-password; length bounds for invite create (quota 1-1000000 or -1, hours 1-87600, note <=100); API-settings length bounds (key<=256, base<=256, model<=64).
  - backend/app/service.py - added `MAX_MESSAGE_LEN=2000` and enforce it in `validate_client_messages` (text length only, images excluded).
  - backend/static/index.html - `maxlength` on login user/pass (20/64), API key/base/model (256/256/64), search (100), chat textarea (2000).
  - backend/static/app.js - `maxlength` on bind/change-password inputs (64), bind user (20), invite note (100); max on number inputs (quota 1000000, hours 87600); frontend validation now enforces 6-64 passwords.
  - BOM-only cleanup in ai/DEPLOYMENT_RUNBOOK.md.
- Verified: `python -m py_compile backend/app/main.py backend/app/service.py` PASS; `node --check backend/static/app.js` PASS.
- Implementation commit: TBD.
- Follow-up / risk: frontend maxlength is a UX guard only; the backend bounds are the real enforcement. No live/paid provider call was made.

### 2026-08-10 - fix custom API test button broken on subpath deployment

- Request / problem: online site at `https://ai.dnbox.cn/fixpilot/` reported frequent errors when using custom API settings.
- Finding / root cause: `testApiSettings_action()` in `backend/static/app.js:2262` used `fetch('/api/test-api', ...)` with a leading slash. The `<base href="/fixpilot/">` tag makes relative URLs resolve correctly, but a URL starting with `/` resolves against the origin only (`ai.dnbox.cn/api/test-api`), bypassing the `/fixpilot/` nginx route and returning 404. This was the only fetch call in the entire app with a leading slash; all other 26 API calls used relative paths.
- Changed: `backend/static/app.js:2262` - changed `'/api/test-api'` to `'api/test-api'`; `backend/static/index.html` - bumped cache tag from `?v=48` to `?v=49`.
- Verified: grep confirms no remaining `fetch('/api` patterns in app.js; commit pushed to origin/main.
- Implementation commit: b6de6d3.
- Follow-up / risk: if the chat itself (not just the test button) also errors, check the server's `backend/logs/api-diagnostics.log` for provider-side errors.

### 2026-08-10 - fix blank page from missing autoResize and redeploy chat UI

- Request / problem: after the API-settings server migration was deployed, the site at `https://ai.dnbox.cn/fixpilot/` showed a blank page (background only). Developer console reported `Uncaught ReferenceError: autoResize is not defined at app.js?v=47:2482:33`, and a hard refresh did not help.
- Finding / root cause: the `autoResize` function was added to `backend/static/app.js` locally but was never committed or pushed, so the server kept serving the old bundle. The version tag in `index.html` was still `?v=47`, so any cached copy also pointed at the stale file.
- Changed:
  - backend/static/app.js - added the `autoResize()` function (input textarea auto-height, max 240px) which the event binding at `input.addEventListener('input', autoResize)` already expected.
  - backend/static/index.html - bumped the script cache tag from `app.js?v=47` to `app.js?v=48`.
- Verified: `git diff` shows exactly the 14-line `autoResize` addition; the bundle now defines the symbol before the event-binding line. Commit pushed to origin/main.
- Implementation commit: 01fdb37 (fix: add autoResize function and bump app.js cache version).
- Follow-up / risk: the online server must pull this commit (`git pull origin main`) and restart uvicorn on port 8135 before the blank page clears. The deleted `backend/app/fixpilot.db` in the working tree was intentionally not committed/deployed; the live DB at `backend/fixpilot.db` is unaffected.

### 2026-08-10 - restrain roast-mode reactions and make shares render them compactly

- Request / problem: the user rejected every canned productized roast line, asked to keep only the harmless approved memes, stop repetitive 6 reactions, add a compact chichi reaction, and fix a shared-link/long-image bug where a 6 bubble expanded like a full answer.
- Finding / root cause: the old server selected a raw 6 without reading conversation history. It had no acknowledgement/review guard, no cooldown, and no once-per-conversation limit. Raw 6 was not a semantic UI record, so share renderers treated it as generic assistant text; flex layout then stretched the bubble. The previous prompt also allowed generic one-line roast interpretation too easily.
- Changed:
  - backend/app/memes.py - added semantic reaction parsing/persistence, legacy raw-6 compatibility, acknowledgement detection, three-reply cooldown, one-six limit, last-meme avoidance, and removed the rejected sick asset from active pools.
  - backend/app/main.py, backend/app/service.py, backend/app/llm.py - pass stored history to effect selection, persist UI-only markers, exclude them from LLM context, and constrain prompt markers to genuinely confirmed harmless blunders without canned text.
  - backend/static/app.js, backend/static/share.html, backend/static/style.css - render compact reaction cards in main chat, admin transcript, share link, and long image; retain old raw 6; remove rejected browser asset.
  - tools/memes_test.py, tools/renderer_test.js, tools/run_all.py - added deterministic no-network reaction and renderer coverage.
  - ai/FixPilot_毒舌项目_v2.0.md, ai/FixPilot_AI人格与毒舌模式_v1.1.md - recorded v2 rule: no fixed roast library; reactions are sparse, context-free UI effects.
  - reports/fixed.md, reports/report20260810_001.md - recorded incident-level and batch-repair evidence.
- Verified: python tools/run_all.py --suites renderer,memes PASS (renderer 7, memes 7); python -m py_compile backend/app/memes.py backend/app/main.py backend/app/service.py backend/app/llm.py PASS; node --check backend/static/app.js PASS; git diff --check PASS. No live/paid model request was made.
- Implementation commit: 16469b0 (fix: restrain roast reactions).
- Follow-up / risk: browser automation cannot initialize in this Codex runtime because its local kernel assets path is missing. Manually check a hard-refresh of one legacy raw-6 conversation and one new reaction in main chat, a share link, and a long image after restarting the local server.

### 2026-08-10 - create a human-and-AI deployment runbook

- Request / problem: establish one deployment/update method that a project owner and any later AI can follow after every Git push, without confusing source control with a live release.
- Investigation: the repository had local start instructions and a short Nginx note, but no production runbook, server inventory, update/rollback procedure, or AI deployment boundary. The requested Trae share URL could not be retrieved through the available web reader because the share host rejected access, so no unverified external instructions were copied into the guide.
- Changed:
  - `ai/DEPLOYMENT_RUNBOOK.md` - added current deployment facts, a recommended single-server baseline, first-deploy templates, every-push update steps, Nginx streaming requirements, backup/rollback procedure, and explicit AI safety boundaries.
  - `ai/README_交接索引.md` - makes the deployment runbook and release gate visible to future handoffs.
- Verified: reviewed current `README.md`, `.gitignore`, `backend/.env.example`, `backend/app/main.py`, `backend/app/db.py`, `backend/app/auth.py`, `backend/requirements.txt`, and `ai/RELEASE_READINESS.md`; `git diff --check` pending after writing. No server access, production deployment, live model call, or sensitive configuration inspection was performed.
- Commit: pending at handoff time.
- Follow-up / risk: the runbook intentionally retains placeholders until the owner supplies the real hosting type, project path, service manager, domain, and backup location. Validate the final commands on the actual server before treating it as an operational record.

### 2026-08-10 - correct deployment runbook to the actual production procedure

- Request / problem: replace a newly written generic deployment guide after the project owner provided the verified real FixPilot procedure. The prior guide incorrectly assumed a systemd/Nginx/8000 deployment instead of the live `/www/wwwroot/fixpilot` + backend `.venv` + port 8135 + `pkill`/`nohup` workflow.
- Investigation: verified the pre-existing incident record in commit `f2ce670` and implementation record `01fdb37`: the actual production blank-page repair used `git pull origin main`, Uvicorn restart at port 8135, `uvicorn.log`, and cache version bump from `app.js?v=47` to `?v=48`. The actual index currently references `app.js?v=48`.
- Changed:
  - `ai/DEPLOYMENT_RUNBOOK.md` - replaced generic/inferred instructions with the confirmed current production path, port, process lifecycle, cache workflow, blank-page incident, bounded safety additions, and AI handoff rules.
- Verified: reviewed `f2ce670`, `01fdb37` record, `reports/fixed.md`, `backend/static/index.html`, and current backend health route. No production connection or command was run by this agent.
- Commit: pending at handoff time.
- Follow-up / risk: the reverse-proxy configuration is still not documented as a verified fact, so the runbook deliberately does not prescribe its management. If the process supervisor/path/port changes, update this runbook in the same deployment change.

### 2026-08-10 - make the first preference choice more visible without blocking chat

- Request / symptom: remove the two explanatory onboarding lines — “这样我知道该讲多细。” and the nudge “选一下，我能少说很多你不需要听的东西。” The cards could be skimmed past and the visually dominant composer invited users to type before noticing the preference choice.
- Finding / design decision: explanatory copy made the screen feel like a setup form and competed with the intended action. The strongest non-blocking nudge is to make the card choice itself describe the immediate benefit, keep the direct-question route subdued, and make cards visibly actionable.
- Changed:
  - `backend/static/app.js` - removed both explanatory strings and the text nudge; changed the first title to “选一下你的电脑熟悉度”; rewrote the three card descriptions as the resulting answer style.
  - `backend/static/style.css` - added a restrained arrow affordance to the title of each selectable card.
  - `backend/static/index.html` - bumped `style.css` cache version 39→40 and `app.js` 49→50.
  - `ai/FixPilot_首次引导与偏好机制_v1.0.md` - appended the v1.1 implementation amendment so future agents preserve the current wording and hierarchy.
- Verified: onboarding static contract PASS (removed copy/text node and old text CSS; expected new copy, arrow affordance, and cache versions present); `node --check backend/static/app.js` PASS; `node tools/renderer_test.js` PASS (R01-R07); `git diff --check` PASS. No live model request or production deployment was performed.
- Commit: pending at handoff time.
- Follow-up / risk: visual browser verification remains needed on desktop and narrow mobile after the next local run; direct entry intentionally remains available and must never be blocked.

### 2026-08-10 - accept concurrent workspace changes and restore local development service

- Request / problem: the owner confirmed that changes visible in the worktree were made by another AI and must be kept as the current baseline, then asked whether the local FixPilot service was deployed.
- Investigation: `git status --short` showed concurrent/unrelated changes (`ai/DEPLOYMENT_RUNBOOK.md`, local SQLite sidecars, `.workbuddy/`, a text file, and a report draft); none were reverted, staged, or modified. No listener initially answered on port 8000. The project-local Uvicorn startup path was verified from `Start-FixPilot.cmd` and `README.md`.
- Changed: no repository source or product-rule file was changed. Started the existing local FastAPI/Uvicorn application from the project virtual environment, bound to `127.0.0.1:8000`.
- Verified: `GET http://127.0.0.1:8000/api/health` returned HTTP 200 with `{"status":"ok","chunks":80}`; `netstat` confirmed `127.0.0.1:8000` is listening (PID 33436 at verification time).
- Commit: none; this is local runtime state only and deliberately does not include concurrent worktree changes.
- Follow-up / risk: the local process is for this workstation session. Restart via `Start-FixPilot.cmd` if it is stopped; do not commit runtime databases, WAL/SHM files, or another agent's unreviewed changes merely to make the worktree clean.

### 2026-08-10 - enlarge the settings surface and compact account credentials

- Request / problem: the fixed desktop settings dialog was too small for the account page; its content area showed a scrollbar and the password action sat at the lower edge. The account/password fields also stretched across nearly the entire wide pane, which looked disproportionate.
- Root cause: `.settings-card` was fixed at `640px × 480px`, while account fields inherited the generic `width: 100%` settings input rule. The account page requires more vertical room than that shared modal budget provided.
- Changed:
  - `backend/static/style.css` - enlarged the desktop settings surface to `720px × 600px`, preserving viewport-safe maximums; limited inputs in `#accountPane` to `min(420px, 100%)` while leaving API and other long-form fields full width.
  - `backend/static/index.html` - bumped only the CSS cache version from `style.css?v=40` to `style.css?v=41`.
- Verified: `node --check backend/static/app.js` PASS; static settings-layout contract PASS; local `GET /style.css?v=41` returned HTTP 200 and contained the new account-input rule; `git diff --check` PASS. No model/API request was made.
- Commit: pending. Concurrent changes from other agents remain intentionally unstaged and preserved.
- Follow-up / risk: browser automation is unavailable in this runtime, so visually confirm the account, API, preferences, and about tabs once at normal desktop zoom and on a narrow mobile viewport. Mobile remains governed by its existing responsive override.
### 2026-08-10 - simplify Volcengine setup and stop pre-filling a specific model

- Request / problem: the dedicated 火山方舟 Responses setup pre-filled `deepseek-v4-flash-260425`, which could be mistaken for the model every user should select. The provider menu also exposed a second 火山方舟 Chat Completions path that the owner does not want to support in the guided UI.
- Root cause: the original preset list encoded one account-specific/example model as a default and exposed two protocols without making their practical distinction useful to FixPilot users.
- Changed:
  - `backend/static/app.js` - removed the dedicated Ark Chat Completions preset and hint; the remaining Ark Responses preset fills only the `/api/v3/responses` endpoint and leaves the model empty with a “copy Model ID from the Ark console” placeholder. Validation now requires the user to provide an enabled Ark model ID. Existing stored `volcengine` settings are shown as a one-time migration form (not silently saved or changed) when settings are opened.
  - `backend/static/index.html` - removed the Chat Completions option, retained only `火山方舟（Responses）`, and bumped `app.js` cache version from v52 to v53.
- Verified: `node --check backend/static/app.js` PASS; static API-preset contract PASS (exactly one Responses preset, no dedicated Chat preset, no old model prefill, Responses-only selector, explicit model-ID validation, legacy form mapping, v53); local `GET /app.js?v=53` returned HTTP 200 with no old model or dedicated Chat preset; `git diff --check` PASS. No model/API call was made.
- Commit: pending. Concurrent worktree changes remain intentionally unstaged and preserved.
- Follow-up / risk: this removes only the guided dedicated Chat option. Full custom API intentionally still permits a compatible `/chat/completions` URL, because it is the escape hatch for providers outside the guided presets. A legacy stored Ark Chat configuration continues serving its old saved behavior until its owner opens settings and consciously saves the Responses form.
### 2026-08-10 - repair the P1 blank-chat send path and add a browser regression contract

- Request / symptom: the owner reported that, on the mobile live site, sending any content (plain text or a photo, with either platform or custom model) cleared the complete chat area. They then authorized use of the already logged-in browser for testing.
- Investigation / root cause: this was provider-independent before the network/model layer. Source history showed `16469b0` removed `fmtMsgTime`, `addMsgTime`, `maybeDivider`, and `scrollDown` while changing the reaction/meme code; later `01fdb37` restored only `autoResize`. In `send()`, the welcome DOM is cleared, then `addMsg('user', content)` calls the now-undefined `maybeDivider()` before it appends a user row. The exception is outside the request `try/catch`, leaving an empty pane. The deployed site was also confirmed to serve `app.js?v=49` / `style.css?v=39`; a no-credential browser contract against that live bundle reproduced `ReferenceError: maybeDivider is not defined` with zero chat rows. The same contract against local `http://127.0.0.1:8000/` after repair gave one user row, one assistant row, and no page errors.
- Changed:
  - `backend/static/app.js` - restored the shared timestamp, time-divider, and scroll helpers as one documented block next to other message UI helpers.
  - `backend/static/index.html` - bumped the browser cache tag from `app.js?v=53` to `app.js?v=54`.
  - `tools/renderer_test.js` - added R08, asserting all shared helpers required by the send/history/reaction paths exist and the direct send placeholder path remains present.
- Verification: no provider/model request and no user credentials were used. `node --check backend/static/app.js` PASS; `python tools/run_all.py --suites renderer,transport` PASS (renderer 8 PASS, transport 3 PASS); browser evidence written to `reports/test-runs/test-20260810-043300-browser-send-path.json`; `git diff --check` PASS. A temporary isolated Chrome used for the browser contract was stopped after verification.
- Commit: pending; no unrelated worktree changes were staged or altered.
- Follow-up / risk: production cannot receive this correction until the owner explicitly requests a commit/push and then applies the verified deployment procedure. After deployment, manually send one short text and one photo on a mobile device with a force refresh; the browser contract proves the client path but deliberately used mocked SSE so it did not spend API quota.
### 2026-08-10 - finalise the P1 helper restoration with encoding-safe time labels

- Request / issue found during verification: a source-codepoint check after the P1 blank-chat fix found that the Windows command transport had encoded the newly restored Chinese cross-day time literals incorrectly. This did not affect the blank-chat root cause but would have made older message dates display mojibake.
- Changed: `backend/static/app.js` now expresses the restored Chinese month/day/yesterday labels as JavaScript Unicode escapes, while keeping the same user-visible output.
- Verified: final browser contract PASS with mocked authenticated SSE: one user row, one assistant row, no page exceptions; explicit browser evaluation returned `8月9日 01:02` and `昨天 04:37`. Evidence: `reports/test-runs/test-20260810-043700-browser-send-path-final.json`. No model/API call or user credential was used.
- Commit: pending with the P1 repair; unrelated worktree changes remain untouched.
### 2026-08-10 - derive transparent candidate assets for the new FixPilot brand mark

- Request / goal: assess `file/logo2026-8-10.png` as a replacement for the current upper-left brand artwork, remove its opaque near-white background, and make small web-ready candidate assets without replacing the live UI prematurely.
- Finding / decision: the supplied source is an RGB-only 2172 x 724 PNG (about 849 KB) with no alpha channel. Its background consists of near-white pixel noise, so deterministic edge-connected background extraction preserves the supplied lettering more faithfully than generative redraw. A mechanical PNG-to-SVG conversion would not create a genuine vector asset and was deliberately not used.
- Changed:
  - `backend/static/assets/fixpilot-brand-lockup-v1.png` and `.webp` - transparent horizontal brand-lockup candidates (512 x 125).
  - `backend/static/assets/fixpilot-brand-mark-v1.png` and `.webp` - transparent square mark candidates (192 x 192) for compact/mobile placement.
- Verified: Pillow opened all four outputs as RGBA; each has both fully transparent and fully opaque pixels. Sizes: lockup WebP 19,920 bytes / PNG 49,851 bytes; mark WebP 12,266 bytes / PNG 31,656 bytes. The original file remains unchanged. The built-in image editing tool was attempted but could not read the Windows workspace path under its restricted-token sandbox, so no generative content was substituted.
- Commit: pending; the assets are candidates only and are not yet referenced by `index.html` or CSS.
- Follow-up / risk: the owner must visually approve the horizontal lockup and compact mark before replacing the existing `logo.svg`. A real SVG should be created only from a design source or a deliberate manual redraw after approval.

### 2026-08-10 - supersede the rejected first logo candidates with the owner-supplied transparent master

- Correction: the preceding v1 candidate assets were visually rejected. They were derived from an older opaque source and are not a suitable representation of the final brand artwork.
- Changed:
  - Removed the four never-referenced `fixpilot-brand-*-v1` candidate files.
  - Used the owner-supplied transparent master `E:/download/ChatGPT_Image_2026年8月10日_11_10_33.png` as the only source; cropped meaningful transparent padding without redrawing it.
  - Added `backend/static/assets/fixpilot-logo-lockup.webp` (512 x 155, 19,936 bytes) and `.png` fallback (55,298 bytes).
  - Added optional compact `fixpilot-logo-mark.webp` (192 x 192, 9,878 bytes) and `.png` fallback (33,212 bytes).
- Verified: all four output files decode as RGBA with alpha extrema `(0, 255)`. The supplied master remains outside the repository and unchanged. No generated imagery or text substitution was used.
- Commit: pending; no UI reference has been changed yet.
- Follow-up / risk: use the lockup only in a location where its existing wordmark will not duplicate nearby `FixPilot` text. Do not globally replace `logo.svg`, because that asset is also used for assistant avatars and login decoration.

### 2026-08-10 - install the approved transparent brand lockup in the application header

- Request / goal: replace only the product's upper-left header logo with the owner-supplied transparent FixPilot lockup, while avoiding duplicated nearby brand text and avoiding an unsafe global replacement of the assistant avatar asset.
- Finding / decision: `logo.svg` is reused for the assistant avatar, login screen, sidebar and generated share content. Replacing it globally with a horizontal wordmark would break those compact uses. The header is therefore the only changed surface; it uses the new lockup and removes the duplicate `FixPilot` name/subtitle block.
- Changed:
  - `backend/static/index.html` - replaced the main `.topbar-left` icon/text pair with a responsive `picture` element that prefers `assets/fixpilot-logo-lockup.webp` and falls back to the transparent PNG; bumped the CSS cache version from v42 to v43 while preserving the concurrent JS cache version v56.
  - `backend/static/style.css` - added desktop/mobile sizing rules for `.topbar-brand-lockup` and removed now-unused topbar title sizing overrides. Desktop width is 142px; mobile is responsive from 86px to 116px.
- Verified:
  - local browser at 1440 x 900: visible lockup 142 x 43, no duplicate old title, no horizontal overflow, no page errors;
  - local browser at 390 x 844: visible lockup 105 x 32, no horizontal overflow, no page errors;
  - browser selected `fixpilot-logo-lockup.webp` with natural dimensions 512 x 155, rather than the PNG fallback;
  - `node --check backend/static/app.js` and `git diff --check` passed. No login, message, image upload, or model call was performed.
- Commit: pending. Concurrent workspace changes remain preserved and unstaged.
- Follow-up / risk: the supplied horizontal mark is intentionally limited to the header. If the owner wants the new illustration in chat avatars or login, review/use the dedicated compact mark separately rather than changing `logo.svg` globally.

- Log correction: the source-file name in the preceding entry was affected by Windows terminal encoding. The asset was unambiguously selected from E:\download using the ASCII suffix *11_10_33.png; the repository outputs, checksums/sizes, and all UI references above are unaffected.

### 2026-08-11 - replace visible product logo surfaces with the owner-supplied v4 artwork

- Request / goal: use `file/logo (1).png` as the new FixPilot logo, process it into transparent WebP assets, and replace the visible header, mobile sidebar, assistant, onboarding, login, and share-image logo surfaces.
- Finding / decision: the supplied source is an opaque RGB 2172 x 724 image with a near-white background. Its supplied artwork was preserved without generative redraw. Edge-connected near-white background extraction retained interior light highlights and created a true alpha channel.
- Changed:
  - `backend/static/assets/fixpilot-logo-lockup-v4.webp` and `.png` - transparent horizontal lockup (512 x 142; WebP 16,556 bytes).
  - `backend/static/assets/fixpilot-logo-mark-v4.webp` and `.png` - transparent compact mark (192 x 192; WebP 7,004 bytes).
  - `backend/static/index.html` - uses the v4 lockup in the header and the v4 mark on login and the mobile sidebar; bumped the application-script cache tag to `app.js?v=58`.
  - `backend/static/app.js` - uses the v4 mark for assistant avatars, welcome/onboarding, and generated long share images; replaced the duplicated inline SVG renderer with the shared compact mark asset.
- Verified: all four generated assets decode as RGBA with alpha extrema `(0, 255)`; static reference contract PASS; `node --check backend/static/app.js` PASS; `git diff --check` PASS. Local browser verification at desktop and 390px mobile widths selected the v4 WebP assets, showed the mobile sidebar mark at 34 x 34, the header lockup at 142 x 39 / 105 x 29, had no horizontal overflow, and reported no page errors. No login, message, image upload, or model/API request was made.
- Commit: none by design; the owner did not request a commit or push. Concurrent worktree changes remain intentionally untouched.
- Follow-up / risk: the browser tab favicon remains its existing independent asset. Earlier v1-v3 candidates are preserved but no longer referenced, so the previous logo can be restored only by an explicit product decision rather than an accidental rollback.

### 2026-08-11 - replace ghost-and-wordmark brand lockups with a complete letters-only wordmark

- Request / goal: remove the ghost from the displayed horizontal product logo after visual review, retain only the `FixPilot` letters, and correct the visibly incomplete `i` caused by the prior lockup crop/extraction.
- Finding / decision: the issue was confined to horizontal branding, not assistant avatars. The wordmark was therefore re-extracted directly from `file/logo (1).png` using the full original text bounds, including both `i` dots and the terminal `t`; no text was regenerated. The compact ghost remains only where it functions as the bot/avatar mark.
- Changed:
  - `backend/static/assets/fixpilot-wordmark-v5.webp` and `.png` - transparent, letters-only source-derived wordmark (512 x 127; WebP 33,012 bytes).
  - `backend/static/index.html` - header and mobile sidebar now use the v5 wordmark; removed the separate sidebar `FixPilot` text to avoid duplicate branding; bumped `style.css` cache tag to v44.
  - `backend/static/style.css` - replaced the square sidebar-mark sizing rule with a left-aligned 112 x 28 wordmark layout.
- Verified: v5 WebP and PNG decode as RGBA with alpha extrema `(0, 255)`; alpha-component validation found the eight glyph bodies and both `i` dots; static header/sidebar reference contract PASS; `node --check backend/static/app.js` PASS; `git diff --check` PASS. No model/API request was made. A temporary local Uvicorn start did not reach a listening socket, so no browser-layout assertion is claimed for this follow-up; the temporary process was stopped.
- Commit: none by design; the owner did not request a commit or push. Concurrent worktree changes remain untouched.
- Follow-up / risk: when the usual local server is next running, visually confirm the v5 header at desktop and mobile widths. The independent favicon and the bot/avatar image remain intentionally unchanged.

### 2026-08-11 - replace the oversized horizontal wordmark with compact text branding and a framed ghost card

- Request / goal: after visual review found the letters-only horizontal wordmark too large and unattractive, restore the earlier compact brand treatment. Place the login-style ghost (white border, rounded card, soft shadow) at the upper-right of the main conversation header, and make the remaining letters smaller.
- Finding / decision: a large raster wordmark is not a good fit for the constrained header. The selected intermediate design uses text for `FixPilot`, preserving legibility at all widths; the ghost is separated into its own small framed decorative card in the header action group. Assistant/chat avatars are unchanged.
- Changed:
  - `backend/static/index.html` - replaced the header and sidebar wordmark pictures with compact `FixPilot` text; restored the small product subtitle in the desktop header; added a `topbar-ghost-card` using the current v4 compact ghost ahead of the header actions; bumped the CSS cache tag to v45.
  - `backend/static/style.css` - added the white, rounded, shadowed ghost-card treatment; set compact text sizing; hides the mobile subtitle and reduces the ghost card to 34px so the action area remains usable.
- Verified: static header/sidebar structure contract PASS; `node --check backend/static/app.js` PASS; `git diff --check` PASS. No model/API request was made. Local browser preview could not be completed because the current local server was not listening on port 8000; a temporary launch attempt failed before spawning due to a PowerShell environment `Path` collision, not a project source error.
- Commit: none by design; the owner did not request a commit or push. Concurrent worktree changes remain untouched.
- Follow-up / risk: visually review the header at normal desktop and mobile widths after starting the usual `Start-FixPilot.cmd`. The v5 wordmark files remain available but are intentionally no longer referenced by the UI.

### 2026-08-12 - restore the original SVG ghost to the left of the compact header name

- Request / goal: replace the unsatisfactory current ghost with the earlier project SVG, position it left of the `FixPilot` text, remove the subtitle below the letters, and remove the brand card from the right-side action group.
- Changed:
  - `backend/static/index.html` - moved a `logo.svg?v=2` ghost card into the left brand block before `FixPilot`; removed the subtitle and the former right-side v4 ghost picture; bumped the CSS cache tag to v46.
  - `backend/static/style.css` - retained the existing white rounded/shadowed card treatment, added the left-brand spacing, and removed the obsolete subtitle/mobile subtitle rules.
- Verified: static brand-header contract PASS (SVG in left block, ghost precedes name, no subtitle, no right-side ghost, desktop/mobile card sizing and cache version present); `node --check backend/static/app.js` PASS; `git diff --check` PASS. No model/API request was made.
- Commit: none by design; the owner did not request a commit or push. Concurrent worktree changes remain untouched.
- Follow-up / risk: visually confirm desktop and mobile alignment after starting the usual local server; this is a purely presentational revision, with no chat/API behavior changed.

### 2026-08-12 - align login branding with the original SVG and remove the tablet composer/toggle collision

- Request / issue: use the original SVG ghost in the login view as well, and prevent the desktop/tablet sidebar-collapse control from overlapping the composer model picker at intermediate widths.
- Finding: login still referenced the compact v4 raster mark while the main header had returned to `logo.svg`. At `min-width: 768px`, `.sidebar-toggle-btn` was absolutely anchored with `bottom: 50px`; this placed it in the same physical lane as the bottom-aligned composer and model menu on tablet-sized layouts.
- Changed:
  - `backend/static/index.html` - both login ghost references now use `logo.svg?v=2`; bumped the stylesheet cache token to `style.css?v=47`.
  - `backend/static/style.css` - desktop/tablet sidebar toggle now anchors to the top-left header lane (`left: 20px; top: 14px`), while the top bar reserves 64px on its left for it. The mobile control remains unchanged and hidden at this breakpoint rule.
- Verified: static layout contract PASS for the two login SVG references, cache token, top-anchored desktop toggle, reserved header lane, absence of the old bottom anchor, and mobile hide rule; `node --check backend/static/app.js` PASS; `git diff --check` PASS. No live model/API call was made. Browser visual verification remains pending because the usual local server was not started during this edit.
- Commit: none by design; the owner did not request a commit or push. Existing concurrent changes and untracked logo assets remain untouched.
- Follow-up / risk: after launching `Start-FixPilot.cmd`, visually inspect a roughly 768-1024px-wide window; the relevant controls should now occupy separate top-header and composer lanes.
### 2026-08-12 - revise the tablet sidebar-toggle placement to a dedicated composer action lane

- Product decision: the owner rejected the top-header placement. The sidebar-collapse control belongs next to the composer, provided it has its own space and never overlaps the model picker.
- Changed: `backend/static/style.css` restores the desktop/tablet control to the composer lane (`bottom: 50px`). On wide layouts it sits in the left gutter of the centered 820px composer; from 768px through 1200px viewport width, `.composer-wrap` uses a 72px left inset and 16px right inset, creating a dedicated 56px action lane. `backend/static/index.html` bumps the stylesheet cache token from v47 to v48.
- Verification: CSS responsive-placement contract PASS (composer-lane anchor, tablet lane, no obsolete topbar reserve, mobile hide rule); `node --check backend/static/app.js` PASS; `git diff --check` PASS. No live model/API call was made; no browser visual assertion is claimed.
- Commit: none by design; the owner did not request a commit or push. Concurrent worktree changes remain untouched.
- Follow-up / risk: open the standard local preview at roughly 768-1024px width. Expected order is sidebar-toggle button, clear gap, then the composer; at wider dimensions the composer remains centered.
### 2026-08-12 - align the composer border with the assistant-bubble content column

- Request: the owner clarified that the composer left edge, not merely its outer wrapper, must align with the leftmost assistant bubble.
- Finding: at tablet width the bot bubble begins 72px from the main-panel edge: 28px chat padding + 34px avatar + 10px flex gap. The previous 72px composer wrapper inset added its own 24px composer padding, placing the visible composer border 24px too far right.
- Changed: `backend/static/style.css` now uses a 48px tablet wrapper inset plus 24px composer padding, placing the visible composer border at the same 72px content line. Above the tablet range, the centered composer is translated right 48px and its sidebar-toggle gutter calculation follows that same column. `backend/static/index.html` bumps the stylesheet cache token to v49.
- Verified: alignment math/static layout contract PASS; `node --check backend/static/app.js` PASS; `git diff --check` PASS. No live model/API call or visual-browser assertion was made.
- Commit: none by design; the owner did not request a commit or push. Existing concurrent changes remain untouched.
- Follow-up / risk: visually inspect the expected line at tablet and wide desktop widths after the standard local launch. The left composer border should align with the first assistant bubble, while the sidebar control sits outside it.
### 2026-08-12 - place the desktop sidebar-toggle in the main panel's lower-left gutter

- Request: the owner clarified that at large desktop sizes the sidebar-collapse control belongs at the lower-left edge of the main panel, not next to the centered composer.
- Finding: the prior wide-screen positioning formula made the control follow the composer content column, contradicting the desired independent lower-left affordance. That relationship is only needed as a collision-avoidance concern on smaller screens.
- Changed: `backend/static/style.css` now uses `left: 20px; bottom: 50px` for the desktop/tablet control. The bubble-aligned composer is unchanged: it remains shifted to the content column on wide screens and gets the tablet left action lane at constrained widths. `backend/static/index.html` bumps the stylesheet cache token to v50.
- Verified: static placement contract PASS (fixed main-left control, bubble-aligned composer, tablet lane, no obsolete centering formula, mobile behavior retained); `node --check backend/static/app.js` PASS; `git diff --check` PASS. No live model/API call or browser visual assertion was made.
- Commit: none by design; the owner did not request a commit or push. Existing concurrent changes remain untouched.
- Follow-up / risk: after the usual local launch, confirm the desktop button is at the main panel lower-left corner and has ample separation from the centered composer.
### 2026-08-12 - make the `6` reaction a normal message and align assistant timestamps

- Request / problem: on shared conversation `vT_xYrQfmXorSxVU`, the standalone `6` was rendered as a conspicuously large, bold reaction card. Timestamp left edges varied between normal assistant replies, reactions, and memes.
- Root cause / decision: all text reactions were forced through `.reaction-card` (18px, weight 650, compact padding), even though `6` is intended to read like an ordinary assistant utterance. Timestamp rules used category-specific left offsets (62px, 48px, and inherited overrides) instead of the actual assistant bubble origin: 34px avatar + 10px message gap = 44px.
- Files changed:
  - `backend/static/app.js` - added a reaction-bubble classifier; `six` now keeps the regular `.bubble` class in live streaming, history/admin replay, and generated shared conversation DOM. Other reactions stay compact.
  - `backend/static/style.css` - normalized assistant, share-image, reaction, and meme timestamp offsets to `44px` with the same 2px vertical spacing.
  - `backend/static/index.html` - bumped static cache tokens to `style.css?v=51` and `app.js?v=59`.
- Verification: pre-change shared-page DOM measurement confirmed `6` used `18px / 650 / 7px 14px`, versus normal reply `15px / 400 / 11px 14px`. `node --check backend/static/app.js` PASS; `git diff --check` PASS. `GET http://localhost:8000/` returns CSS v51 and app v59; served v59 contains the normal-six renderer and served v51 contains both normalized timestamp rules. Browser reattach after reload timed out, so a final manual visual refresh remains useful.
- Commit: none by design; the owner did not request a commit or push. Existing concurrent changes and assets remain untouched.
- Follow-up / risk: after a normal refresh of the local share page, `6` should use the same font weight/size/padding as an ordinary assistant one-character message and all assistant-side timestamps should start directly under the bubble's left edge.
### 2026-08-12 - correction: fix the standalone shared-conversation renderer for `6` and timestamp alignment

- Request / problem: the owner refreshed shared conversation `vT_xYrQfmXorSxVU` and correctly found that the earlier `6` and timestamp fix had no effect on the public share page.
- Correction to prior investigation: the earlier entry covered the live/history/admin renderer in `app.js` and common `style.css`, but incorrectly described the share link as covered. `/share/{token}` serves the independent inline renderer in `backend/static/share.html`; it does not load the application's common CSS or JS.
- Root cause: `share.html` still hard-coded every text reaction as `.reaction-card` and removed the normal timestamp padding for reactions/memes. Thus `6` remained `18px / 650 / 7px 14px`, while its visible timestamp began 14px left of normal assistant text.
- Files changed: `backend/static/share.html` - added the same `six -> bubble` classifier used by the main client and restored the normal timestamp inset for reaction and meme rows.
- Verification: reloaded the actual local share URL in the browser. Both a normal assistant message and `6` measure `15px / 400 / 11px 14px`; their visible text and timestamp positions are both 74px from the viewport left. No model/API request was made. `git diff --check` PASS.
- Commit: none by design; the owner did not request a commit or push. Existing concurrent changes and untracked assets remain untouched.
- Final status: fixed and browser-verified on the actual standalone share page.
### 2026-08-12 - make standalone shared-conversation timestamps follow the main-chat interaction model

- Request / decision: the owner chose consistent behavior over permanently visible share-page timestamps. Timestamps on the public share view should remain hidden until the reader hovers the corresponding message, just like the main chat.
- Changed: `backend/static/share.html` - replaced the independent always-visible timestamp rule (`opacity: 0.7`) with the main-chat visual contract: hidden by default, 180ms fade-in on `.msg:hover`, same low-emphasis typography and retained layout space so hovering does not shift messages.
- Verification: the local server's actual `/share/vT_xYrQfmXorSxVU` response contains the new default-hidden and hover rules, no longer contains the old always-visible declaration, and retains the previously verified normal-six renderer plus timestamp alignment rules. `git diff --check` PASS. No live model/API call was made.
- Commit: none by design; the owner did not request a commit or push. Existing concurrent changes and untracked assets remain untouched.
- Final status: complete locally. Touch-only devices will keep timestamps hidden because there is no persistent hover state; this is intentional for visual consistency, and can later be revisited only if the owner wants a mobile-specific interaction.