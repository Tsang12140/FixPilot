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
