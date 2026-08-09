> **Required before implementation:** read [`../AGENTS.md`](../AGENTS.md) and
> [`WORK_LOG.md`](WORK_LOG.md) first. Every completed task must append a
> verified handoff entry to `WORK_LOG.md` before commit or handoff.

# FixPilot AI 产品规则包 v1.0

> 交接对象：继续负责 FixPilot 实现/迭代的 AI 或开发者  
> 日期：2026-08-08

本规则包用于把 FixPilot 当前正在形成的 AI 产品逻辑从聊天讨论沉淀为可实现、可测试、可维护的规范。

---

## 文档阅读顺序

### 0. FixPilot 产品背景资料
这是当前项目事实来源，应先读。

重点确认：

- 已实现
- 已确定未实现
- 仅讨论
- 真实模型能力边界
- 当前数据库
- 当前 System Prompt
- OCR / RAG / JOKE6 / 配额 / 会话逻辑

### 1. FixPilot 用户技术水平判定系统 v1.0
定义：

- beginner / intermediate / advanced
- 有效画像轮次
- 自动推断
- evidence / strength
- confidence
- 显式选择优先
- 动态纠正

### 2. FixPilot 首次引导与偏好机制 v1.0
定义：

- 首次欢迎区两步卡片
- 跳过
- 二次轻引导
- 默认行为
- 偏好保存
- 设置页修改

### 3. FixPilot 对话人格与表达矩阵 v1.0
定义：

- normal / roast / concise
- 3×3 水平与语气矩阵
- JOKE6 边界
- AI 腔控制
- 画像提示文案

### 4. FixPilot 诊断置信度与问诊决策规则 v1.0
定义：

- D0-D4 诊断状态
- 弱/中/强证据
- 下一问题如何选择
- 什么时候给方案
- 防止过度确定

### 5. FixPilot 高风险操作与停止指导规则 v1.0
定义：

- R0-R3 风险等级
- BIOS / BitLocker / 磁盘 / 数据恢复 / 拆机等
- 什么时候必须确认
- 什么时候停止远程指导
- 什么时候建议送修

### 6. FixPilot Prompt 分层与运行时编排规范 v1.0
定义：

- Base / Diagnostic / Safety / Profile / Style / Knowledge 六层
- Level Classifier 与主回答分离
- 与现有 OCR / RAG / JOKE6 的兼容方式

---

## 工作方法论

### FixPilot Bug 检索与修复流程 v1.1
[`FixPilot_分层Bug检索与修复流程_v1.0.md`](FixPilot_分层Bug检索与修复流程_v1.0.md)

两阶段：Phase A 通用排查（70%，主体）——不预设种子，按 10 类检查矩阵（编码/真值兜底/前后端契约/多AI重复实现/注入越权/流式协议/错误吞没/并发时序/边界校验/死代码）逐类主动扫全库，只读只报告；Phase B 分层扩大（30%）——把 Phase A 捞出的每个 Bug 当种子，跑 Layer 0-3（锚定→同模式横扫→根因升华搜变体→修复回归加固）顺藤摸瓜挖同类项。任何接手 AI 应先用 Phase A 广撒网，发现问题后再用 Phase B 扩大战果。

---

## 实现原则

1. 先保证现有问诊功能不回退。
2. 小范围产品，不为“架构漂亮”做过度工程化。
3. 用户显式选择优先。
4. 画像是辅助，不是用户标签系统。
5. 人格只改变表达，不改变事实和安全规则。
6. 高风险护栏优先于“少废话”和“毒舌”。
7. 自动判断尽量结构化输出，避免把内部 metadata 混进用户正文。
8. 每个新增规则都应该可以单独测试。

---

## 推荐实施顺序

### Phase 1
- 增加 profile 数据结构
- 首次两步偏好引导
- 设置页偏好修改
- Prompt 读取 level / style

### Phase 2
- 增加 Level Classifier
- 有效轮次计数
- inferred profile
- 画像提示一次

### Phase 3
- 诊断 D0-D4 规则注入
- 安全 R0-R3 规则注入
- 高风险确认与停止指导

### Phase 4
- 测试集
- 调整误判
- 优化人格
- 再考虑长期记忆、复杂 Agent 或工具调用

---

## 当前不要急着做

- 微服务拆分
- 向量长期记忆系统
- 复杂工作流引擎
- 多 Agent 编排
- 完整用户行为数据平台
- 为 3 档画像建立复杂机器学习模型

当前 FixPilot 规模下，简单、透明、容易调试优先。

---

## 验收目标

当这套规则落地后，用户应明显感受到：

> 第一次可以自己选 FixPilot 怎么跟我说；不选也不妨碍使用。聊几轮后，它会逐渐知道我懂多少。它有性格，但真正修电脑时不会乱开玩笑。它不会因为看到一个错误码就瞎断言，也知道什么时候不能再让我继续乱试。

## 部署与上线

部署、服务器更新、上线与回滚前，必须阅读：

- [`DEPLOYMENT_RUNBOOK.md`](DEPLOYMENT_RUNBOOK.md)：当前 FixPilot 的部署、每次 push 后更新、回滚和 AI 权限边界。
- [`RELEASE_READINESS.md`](RELEASE_READINESS.md)：邀请制 Beta 与公开发布的上线门槛。

`git push` 仅更新 GitHub，**不代表线上服务已更新**。不得猜测服务器路径，或处理生产数据库、密钥与 `.env`。
