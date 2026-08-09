# FixPilot 测试体系

这里的文件把“跑一下脚本”变成可重复的产品验证流程。

阅读顺序：

1. TESTING_PLAYBOOK.md：任何 AI 收到“我要测试”后必须遵循的工作流。
2. FixPilot_TEST_PROFILE.md：FixPilot 的真实模块、场景、风险和完成标准。
3. PROJECT_TEST_PROFILE.template.md：新项目复制后改造成自己的测试档案；不要直接照搬 FixPilot 场景。
4. tools/：可运行的 FixPilot 测试实现。

## 给后续 AI 的触发语义

在本仓库，用户说“我要测试”“跑测试”“回归测试”“测一下这个改动”，都不是只做编译检查。应先读取本目录的工作流和 FixPilot 测试档案，再按改动范围选择测试模块。

如果 AI 所在平台不会自动读取 AGENTS.md，用户可以补这一句：

> 我要测试。请先读取 AGENTS.md、ai/Testing/README.md 和 ai/Testing/FixPilot_TEST_PROFILE.md，按仓库测试工作流执行，不要只做静态检查。

## 目录边界

- tools/testkit.py：可复用的传输层，负责认证、建会话、图片编码、SSE 解析和统一的失败分类。
- tools/scenarios.py、persona_test.py：FixPilot 专属的动态故障真相和人设回归。
- tools/injection_test.py：FixPilot 专属注入边界。
- tools/safety_test.py：FixPilot 专属风险提示与停止指导。
- tools/run_all.py：模块化入口，默认产出本地 JSON 证据。

测试运行产生的 JSON 默认放在 reports/test-runs/，保留在本机、不会误加入提交。经过人工确认的重要失败，才整理为 reports/reportYYYYMMDD_NNN.md；实际修好的单项 Bug 仍按仓库铁律追加 reports/fixed.md。


## Automated renderer check

For response-layout regressions, run `python tools/run_all.py --suites renderer`. This invokes `tools/renderer_test.js`; it is credential-free and does not call a model.

## Transport and risk-guardrail check

For changes to streamed replies, empty-reply handling, retry behavior, or the
trusted risk-notice fallback, run:

```bash
python tools/run_all.py --suites renderer,transport
```

`tools/transport_test.py` is credential-free and never calls a provider. It
checks that direct BIOS changes and driver removal/reinstallation receive the
right preflight risk level, that an empty stream plus empty fallback retries
exactly once, and that visible streamed text never triggers a duplicate retry.

## Web-search boundary check

For the one-turn official DeepSeek V4 Flash “查资料” feature, run:

```bash
python tools/run_all.py --suites renderer,transport,websearch
```

`tools/web_search_test.py` is credential-free. It checks the official host/model gate,
server-decided tool availability without `tool_choice`, removal of the user control, source
disclosure only after an actual lookup, priority routing for curated official sources, safe
broadening for concrete unlisted documentation requests, and rejection of other providers before any network request.


## Official source registry

The curated source catalogue has both a deterministic integrity test and a separate live, read-only URL audit. Run these after changing `data/official_sources.json`:

```powershell
python tools/official_sources_test.py
python tools/official_sources_audit.py --enabled-only
```

The first command must pass before a commit. The second may report `review_needed` for vendor bot protection or network failures; do not auto-enable a candidate based only on a search result.
