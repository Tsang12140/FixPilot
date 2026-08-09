# FixPilot 人设测试框架 - AI 交接说明

> 写给下一个接手的 AI。读完这份就能知道：我们做了什么、当前状态、要做什么。
> 最后更新：2026-08-09（Asia/Shanghai）

## 一、背景：为什么做这件事

FixPilot 是电脑故障排查 AI 助手（FastAPI + DeepSeek）。之前用预设对话剧本测，测不出真东西——AI 按剧本走，跟真实用户 unpredictable 的对话差太远。

用户要求改成：**存完整故障真相（症状/硬件/时间线/结局），陪练 AI 拿事实动态应答 FixPilot 的提问**。人设（小白/中白/大白）只影响"怎么说"，不改变事实。

## 二、我们做了什么

### 1. 创建了 `tools/` 测试工具集

```
tools/
├── scenarios.py          # 故障真相数据集（9个场景，核心）
├── persona_test.py       # 人设渐进式对话测试引擎
├── injection_test.py     # 12类提示词注入测试
├── run_all.py            # 一键跑全部测试
├── images/               # 测试用图片（4张）
│   ├── bsod_0x7e.jpg
│   ├── device_manager_yellow.jpg
│   ├── error_0xc0000005.jpg
│   └── task_manager_high_mem.jpg
├── persona_results.json  # 最新人设测试结果
└── injection_results.json # 最新注入测试结果
```

### 2. `scenarios.py` - 故障真相数据集（核心）

**存的是"完整故障情况"，不是对话剧本。** 每个场景两块：

- **facts**：模拟用户已知的事实
  - `initial_complaint` 第一句模糊主诉
  - `symptoms` 能被问出来的症状细节
  - `hardware` 硬件配置（按人设能说清的程度）
  - `timeline` 事发前经过
  - `prior_attempts` 已经试过的操作
  - `capabilities` 能力限制（不敢拆机等）
  - `action_outcomes` FixPilot 让你做某操作后的结果（含 `solves: true` 标记）
  - `images` 能提供的图片 + 何时发

- **grading**：评分点（陪练 AI 不知道，测试引擎用来判 FixPilot 是否查对方向）
  - `root_cause` 真实根因
  - `solution` 真实修复
  - `key_evidence` 关键证据关键词
  - `stop_when` 达成判定

**9 个场景分布：**
| ID | 人设 | 故障 |
|----|------|------|
| B01 | 小白 | 内存条松动蓝屏 |
| B02 | 小白 | 浏览器吃内存卡顿 |
| B03 | 小白 | 开机没反应/插座没电 |
| I01 | 中白 | 蓝屏 0x7E 驱动冲突 |
| I02 | 中白 | 休眠唤不醒黑屏 |
| I03 | 中白 | 0xc0000005 应用报错 |
| A01 | 大白 | 蓝屏 0x7E 金手指氧化 |
| A02 | 大白 | 高频蓝屏电源 12V 老化 |
| A03 | 大白 | 网卡 PCIe 接触不良 |

### 3. `persona_test.py` - 动态应答测试引擎

工作流程：
```
scenarios.py (故障真相 facts)
    ↓ 陪练 AI (deepseek-chat) 拿 facts 扮演用户，动态应答 FixPilot 的提问
    ↓ FixPilot 后端 (http://127.0.0.1:8000) SSE 流式回复
    ↓ _record_bugs() 自动检测 bug：http_error / empty_reply / image_not_seen
    ↓ grading.key_evidence 判 FixPilot 是否查对方向
    ↓ [SOLVED] 标记结束对话
```

关键设计：
- **陪练 AI**：deepseek-chat，自动读 `backend/.env` 配置，兼容 DeepSeek/Ark
- **图片发送**：用 OpenAI 多模态格式 `[{"type":"text",...},{"type":"image_url",...}]`
- **图片标记**：陪练 AI 输出 `[IMG:path]` 时发图
- **解决标记**：陪练 AI 输出 `[SOLVED]` 时结束对话

### 4. `injection_test.py` - 12类注入测试

12 类边界攻击测试：忽略指令、越狱、敏感词、管理员指令等。**已全部通过**。

### 5. `run_all.py` - 一键入口

```bash
# 跑全部（注入 + 人设）
python tools/run_all.py --base http://127.0.0.1:8000 --admin-user <configured-admin> --admin-pass <configured-password>

# 只跑人设
python tools/run_all.py --skip-injection --admin-user <configured-admin> --admin-pass <configured-password>

# 只跑某个 人设
python tools/run_all.py --skip-injection --persona beginner --admin-user <configured-admin> --admin-pass <configured-password>

# 只跑人设（直接调用 persona_test.py）
python tools/persona_test.py --base http://127.0.0.1:8000 --admin-user <configured-admin> --admin-pass <configured-password> --max-rounds 16
```

## 三、已完成的测试

### 注入测试
12 类全过，防御有效。

### 人设测试（9场景 / 71轮对话）

| ID | 轮次 | 查对方向 | 解决 | 状态 |
|----|------|----------|------|------|
| B01 | 9 | 是 | 是 | 无 bug |
| B02 | 7 | 是 | 是 | 无 bug |
| B03 | 7 | 是 | 是 | 无 bug |
| I01 | 8 | 是 | 是 | 无 bug |
| I02 | 8 | 是 | 是 | 无 bug |
| I03 | 11 | 是 | 否 | 有 bug（P1）|
| A01 | 3 | 是 | 是 | 无 bug |
| A02 | 12 | 是 | 是 | 有 bug（P2）|
| A03 | 6 | 是 | 是 | 有 bug（P2）|

**8/9 解决，9/9 查对方向。** 详见 `reports/report20260809_002.md`。

## 四、发现的 bug

### P1 - I03 R11 HTTP 500 空回复（未修复）

- **类型**：http_error / empty_reply
- **conv_id**：`c72dd6831137cedd4`
- **现象**：中白场景 I03 测试到第 11 轮，陪练 AI 回答了 DEP 设置状态后，FixPilot 后端返回 HTTP 500，SSE 流输出 `__error__:服务没有返回可显示的回复，请重试。`，对话中断。
- **可能原因**：DeepSeek API 偶发超时/限流（对话已到 11 轮，上下文较长）；或 RAG 检索命中异常知识块导致 prompt 过长。
- **怎么查**：
  ```bash
  grep "c72dd6831137cedd4" backend/logs/api-diagnostics.log
  ```

### P2 - AI 主动说"看不了图"拒绝图片（已修复）

- **类型**：product_behavior_error
- **conv_id**：A03 = `ca15a5992ababc0a5`，A02 = `c0ced5db8d1a8fbdc`
- **现象**：A03 R2 用户说"我拍个图给你看"，AI 回"别发图，我看不了图"；A02 R6 类似。
- **根因**：[backend/app/llm.py:13](file:///d:/personal/cc/FixPilot/backend/app/llm.py#L13) BASE_POLICY 写了"不能真正看图"，AI 理解成"不能接收任何图片"，于是主动拒绝——但 FixPilot 实际有 OCR 管道能识别截图文字。
- **修复**：改为"能识别截图文字（蓝屏代码、错误框等），但不能看硬件外观"，并加"不要说'看不了图'或拒绝接收"。后端已重启生效。
- **状态**：已修复，待重跑 A03 验证。

### P3 - 测试覆盖缺口：陪练 AI 全程没发图（未修复）

- **类型**：test_coverage_gap
- **现象**：5 个场景配了图片，但陪练 AI（deepseek-chat）在 71 轮对话中从未输出 `[IMG:path]` 标记。
- **影响**：OCR 管道完全没被测到。P2 bug 是 AI 主动暴露的，不是因为图发过来后 OCR 失败才发现的。
- **可能原因**：陪练 AI 的 system prompt 中图片发送指引不够强。
- **建议**：强化 `persona_test.py` 的 `tutor_respond` 指引，当 FixPilot 主动问截图/拍照时强制输出 `[IMG:path]`。

## 五、要做什么（接手任务清单）

### 任务 1：修复 P1（HTTP 500 空回复）
1. 查 `backend/logs/api-diagnostics.log` 中 conv_id `c72dd6831137cedd4` 的错误
2. 判断根因：超时？限流？prompt 过长？RAG 异常？
3. 修复方向：
   - 如果是超时：加请求超时和重试逻辑（`backend/app/llm.py` 的 `stream_chat`）
   - 如果是上下文过长：加对话历史截断（保留最近 N 轮 + system prompt）
   - 如果是 RAG 异常：检查 `retriever.retrieve` 返回的内容
4. 修复后在 `reports/report20260809_002.md` 的 P1 小节末尾追加 `#### 修复`

### 任务 2：修复 P3（陪练 AI 不发图）
1. 改 `tools/persona_test.py` 的 `tutor_respond` 函数中的 system_prompt
2. 强化图片发送指引：当 FixPilot 主动问"截图/拍照/发图"时，必须输出 `[IMG:path]`
3. 或在 `scenarios.py` 的 `facts.images` 中增加 `must_send_round` 字段
4. 重跑测试验证陪练 AI 会发图
5. 修复后在 `reports/report20260809_002.md` 的 P3 小节末尾追加 `#### 修复`

### 任务 3：验证 P2 修复
1. 重跑 A03 场景：`python tools/persona_test.py --persona advanced --admin-user <configured-admin> --admin-pass <configured-password>`
2. 确认 AI 不再说"看不了图"

### 任务 4：全部修完后按铁律收尾
1. **改名**：`reports/report20260809_002.md` → `reports/report20260809_002-fixed.md`（全部 bug 修完才能改）
2. **报告内**：
   - 顶部速览表「状态」列全部标「已修复」
   - 每条 bug 详情末尾的 `#### 修复` 小节补全（P1/P3 补上）
3. **`reports/fixed.md` 追加**：P1 和 P3 的 concise event（P2 已有）
4. **`ai/WORK_LOG.md` 追加**：任务级记录

## 六、铁律提醒（必须遵守）

### 禁用"小点"符号
永久禁用：`·` `•` `●` `◦` `‣` `・` 等装饰性圆点。替代：中文并列用 `、`，技术备选用 `/`，标题分隔用 ` - `。

### Bug 报告归档
- 报告存 `reports/`，命名 `reportYYYYMMDD_三位数字.md`
- 全部 bug 修复后改名加 `-fixed` 后缀
- 修复后在每条 bug 详情末尾追加 `#### 修复` 小节（file:line、改法、验证）
- 顶部速览表加「状态」列
- 报告开头标注修复日期

### 每条 bug 修复追加 `reports/fixed.md`
日期时区、修复 agent、症状、根因、改的文件、验证、状态、commit hash。

### 每个任务追加 `ai/WORK_LOG.md`
request、root cause、files changed、verification、commit、follow-ups。

## 七、关键文件速查

| 文件 | 作用 |
|------|------|
| `tools/scenarios.py` | 故障真相数据集（9场景），改场景内容改这里 |
| `tools/persona_test.py` | 测试引擎，改陪练 AI 行为改这里 |
| `tools/run_all.py` | 一键入口 |
| `backend/app/llm.py` | FixPilot 的 system prompt（P2 改的就是这里第 13 行）|
| `backend/app/service.py` | 多模态消息处理 + OCR 调用 |
| `backend/app/ocr.py` | 本地 OCR（RapidOCR）|
| `reports/report20260809_002.md` | 当前测试报告（P2 已修，P1/P3 未修）|
| `reports/fixed.md` | per-bug 修复记录（P2 已有，P1/P3 待补）|
| `ai/WORK_LOG.md` | 任务级交接日志 |
| `backend/.env` | 陪练 AI 自动读这里配置 |

## 八、运行前提

1. 后端在跑：`cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. 管理员账号：admin / <configured-password>（见 `backend/.env`）
3. 测试会消耗 DeepSeek API 配额（管理员账号用自己 API 不扣次数）
4. 测试图片在 `tools/images/`（已生成 4 张）
