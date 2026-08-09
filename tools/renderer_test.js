#!/usr/bin/env node
/*
 * No-browser regression checks for FixPilot's answer renderer.
 * This intentionally exercises the same pure frontend functions that render
 * assistant messages, so a tester does not need to handcraft browser input.
 */
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const appPath = path.join(root, 'backend', 'static', 'app.js');
const cssPath = path.join(root, 'backend', 'static', 'style.css');
const sharePath = path.join(root, 'backend', 'static', 'share.html');
const source = fs.readFileSync(appPath, 'utf8');
const css = fs.readFileSync(cssPath, 'utf8');
const share = fs.readFileSync(sharePath, 'utf8');

function fail(message) {
  throw new Error(message);
}
function assert(condition, message) {
  if (!condition) fail(message);
}
function extract(startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start);
  if (start < 0 || end < 0) fail(`renderer source markers missing: ${startMarker}`);
  return source.slice(start, end);
}

const markdown = extract('function escapeHtml(s)', '/* ---------- DOM ---------- */');
const options = extract('const MAX_CLICKABLE_OPTIONS = 4;', 'const RISK_NOTICES = {');
eval(`${markdown}\n${options}`);

const results = [];
function check(id, name, fn) {
  try {
    fn();
    results.push({ id, name, status: 'PASS' });
  } catch (error) {
    results.push({ id, name, status: 'FAIL', detail: error.message });
  }
}

check('R01', 'ordinary numbered instructions remain message text', () => {
  const text = '\u6309\u4e0b\u9762\u505a\uff1a\n1. \u5378\u8f7d\u65e7\u9a71\u52a8\n2. \u91cd\u542f\u540e\u5b89\u88c5\u65b0\u7248';
  const parsed = parseOptions(text);
  assert(parsed.main === text, 'ordinary numbered text was changed');
  assert(parsed.options.length === 0, 'ordinary numbered text became option cards');
});

check('R02', 'only explicit option marker creates option cards', () => {
  const text = '\u5148\u786e\u8ba4\u53d1\u751f\u573a\u666f\u3002\n\u9009\u9879\uff1a\n1. \u53ea\u5728\u6e38\u620f\u65f6\u84dd\u5c4f\n2. \u65e5\u5e38\u4f7f\u7528\u4e5f\u4f1a\u84dd\u5c4f';
  const parsed = parseOptions(text);
  assert(parsed.main === '\u5148\u786e\u8ba4\u53d1\u751f\u573a\u666f\u3002', 'option prefix was not preserved');
  assert(parsed.options.length === 2, 'explicit options were not recognized');
});

check('R03', 'unmatched Markdown fence cannot hide reply tail', () => {
  const html = mdToHtml('\u84dd\u5c4f\u4ee3\u7801\u662f 0x7E\n```\n\u4e0d\u8981\u628a\u540e\u6587\u541e\u6389');
  assert(!html.includes('<pre><code>'), 'unmatched fence opened a code block');
  assert(html.includes('\u4e0d\u8981\u628a\u540e\u6587\u541e\u6389'), 'reply tail is missing');
});

check('R04', 'question-mark-only titles have a safe fallback', () => {
  assert(safeDisplayText('?????', '\u672a\u547d\u540d\u5bf9\u8bdd') === '\u672a\u547d\u540d\u5bf9\u8bdd', 'corrupt title fallback failed');
});

check('R05', 'bot and share bubbles are left aligned', () => {
  const bot = css.match(/\.msg\.bot \.bubble\s*\{([^}]*)\}/);
  const share = css.match(/\.share-node \.msg\.bot \.bubble\s*\{([^}]*)\}/);
  assert(bot && /text-align:\s*left/.test(bot[1]), 'main bot bubble is not left aligned');
  assert(share && /text-align:\s*left/.test(share[1]), 'shared bot bubble is not left aligned');
});

check('R06', 'semantic reactions render compactly in chat and shares', () => {
  assert(source.includes('function reactionIdFromMessage'), 'chat reaction parser is missing');
  assert(source.includes('reaction-card'), 'chat reaction card is missing');
  assert(css.includes('.msg.bot .bubble.reaction-card'), 'chat compact reaction CSS is missing');
  assert(share.includes('function reactionIdFromMessage'), 'share reaction parser is missing');
  assert(share.includes('.msg.bot .bubble.reaction-card'), 'share compact reaction CSS is missing');
});

check('R07', 'rejected meme is absent from active browser allowlists', () => {
  assert(!/\bsick\s*:/.test(source), 'chat still exposes rejected meme');
  assert(!/\bsick\s*:/.test(share), 'share still exposes rejected meme');
});

const output = { suite: 'renderer', results };
const failed = results.some(item => item.status !== 'PASS');
if (process.argv.includes('--json')) {
  process.stdout.write(JSON.stringify(output));
} else {
  for (const item of results) {
    process.stdout.write(`[${item.id}] ${item.name}: ${item.status}${item.detail ? ` (${item.detail})` : ''}\n`);
  }
}
process.exitCode = failed ? 1 : 0;
