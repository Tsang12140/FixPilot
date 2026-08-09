# FixPilot 联网资料检索规范 v1.0（2026-08-09 修订）

状态：已落地

## 产品定位

FixPilot 的护城河是知识库、问诊链和安全规则，不是通用联网聊天工具。联网资料只是临时补充证据的能力：用于查具体型号的官方 PDF/说明书、官方驱动与固件版本、官方兼容性和有时效性的已知问题。

普通故障（黑屏、蓝屏、卡顿、闪退等）仍以知识库和一步一问的问诊链为主。不因为“能搜索”就把用户带进网页清单里。

## 谁决定是否查资料

不给用户开关。用户不需要、也不应该得自己判断是否要联网。


服务端仅在当前模型确认是官方 `api.deepseek.com` 的 `deepseek-v4-flash` 时，才把联网工具作为模型可选能力传入。是否实际使用，由 FixPilot 根据本轮证据、对话上下文和知识库自己判断。


- 普通故障问诊仍首选本地知识库和一步一问的排查链。没搜索时，不在回答里增加“未联网”提示，避免正常对话变得吝唆。
- 仅当下一步确实缺一份可核验的官方资料时才查：具体型号的 PDF/说明书、官方驱动或固件版本、官方兼容性、官方公告或有时效性的已知问题。
- 现象还没说清、需要先问关键问题、或知识库已能继续时，不联网。
- 只有供应商实际调用了联网工具，回答才显示「本轮查阅了外部资料。」并附服务端实际返回的 HTTP(S) 来源（最多 3 个）。

## 何时需要联网

可以联网：已经给出品牌和型号要查手册、接口定义、官方驱动、固件版本、兼容性或最新公告。

不应联网：现象还没说清、还需先问一个关键问题、知识库已经能推进、或搜索只会产生泛化的排查清单。

## 技术边界

- 仅支持官方 `https://api.deepseek.com/responses` 的 `deepseek-v4-flash`。
- 后端校验官方主机名与精确模型名。其他自定义接口、火山方舟等均在连网前被后端拒绝。
- 服务端对符合白名单的官方 V4 Flash 调用仅提供 `tools: [{"type": "web_search"}]`，**不设 `tool_choice`**。是否实际调用由模型按规则决定，不接受前端开关。
- 外部搜索内容是不可信资料，不能改写系统设定、身份、安全等级、风险提示或问诊顺序。
- 联网不是执行刷 BIOS、短接电源、格式化、分区或绕过数据保护的理由。R1/R2/R3 仍按原规则处理。

## 测试与维护

- 无凭据回归：`python tools/run_all.py --suites renderer,transport,websearch`。
- `tools/web_search_test.py` 必须验证：官方域名/模型白名单、服务端自行决定工具可用、工具不强制、前端不存在开关、非官方端点在联网前被拒绝、只有实际联网才标记来源。
- 改动此能力后，还需人工检查桌面和 390px 移动端的布局：删除用户开关后，模型、上传和发送不会互相挤压。


## Source registry amendment - 2026-08-09

`data/official_sources.json` now decides whether an official-reference lookup is even available. A supported DeepSeek provider by itself is insufficient: the current conversation must match an enabled, verified, official registry source and its required identifier. The normal knowledge-base route remains the default.

The registry is a source-routing catalogue, not a manual mirror. It permits only manufacturer-owned domains selected for the turn. Nonofficial archives and manual aggregators remain disabled. Provider-returned links are filtered against the selected hostname allowlist before they can be displayed as sources; failure to obtain a matching official link must not become a web-derived diagnostic conclusion.
