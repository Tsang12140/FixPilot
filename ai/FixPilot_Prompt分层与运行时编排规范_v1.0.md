# FixPilot Prompt 分层与运行时编排规范 v1.0

> 文档性质：AI Architecture / Prompt Engineering 规范  
> 状态：v1.0 设计稿  
> 适用范围：System Prompt 拆分、用户画像注入、诊断规则注入、RAG/OCR 与主模型协作  
> 设计日期：2026-08-08

---

## 1. 目标

FixPilot 后续会同时拥有：

- 问诊规则
- 用户水平
- 语气偏好
- 自动画像
- 诊断置信度
- 安全边界
- RAG
- OCR
- JOKE6

如果全部继续堆在一个不可维护的大 System Prompt 中，规则之间容易互相污染。

因此采用：

> **逻辑分层，运行时再拼接。**

不要求一开始引入复杂 Agent 框架。

---

## 2. 推荐的六层结构

### Layer 1｜Identity / Base Policy

永远不变。

负责：

- FixPilot 是电脑故障排查助手
- 中文
- 不假装具备不存在的能力
- OCR 能力边界
- 不联网/不远程/不运行命令等真实边界
- 回复总体长度
- 禁 emoji / 装饰圆点

---

### Layer 2｜Diagnostic Policy

负责：

- 医生问诊式交互
- 一次只推进一步
- 一次只问一个关键问题
- D0-D4 诊断状态
- 证据强度
- 何时给解决方案
- 如何表达不确定性

---

### Layer 3｜Safety Policy

负责：

- R0-R3 风险分级
- 数据安全
- BitLocker/BIOS/磁盘/拆机等边界
- 停止指导条件
- 送修条件

该层优先级高于 Style。

---

### Layer 4｜User Profile

运行时动态注入。

示例：

```text
用户技术水平：intermediate
来源：explicit
置信度：high
表达偏好：concise
```

如果水平未知：

```text
用户技术水平：unknown
不要假设用户是小白或高手；根据本轮表现临时适配。
```

---

### Layer 5｜Style Policy

根据 `response_style` 注入：

- normal
- roast
- concise

只负责“怎么说”。

不得改变：

- 诊断结论
- 安全规则
- 事实标准

---

### Layer 6｜Knowledge Context

现有 BM25 RAG 检索结果。

继续保留：

- 知识库优先
- 未覆盖时明确说明
- 不把检索片段当绝对真理
- 与用户实时证据冲突时，以当前用户证据为准并继续验证

---

## 3. 推荐优先级

从高到低：

```text
安全规则
> 能力/事实边界
> 诊断规则
> 用户显式设置
> 用户推断画像
> 语气人格
> RAG 表述细节
```

重要：

> roast / concise 永远不能覆盖 Safety。

---

## 4. 自动水平判定器应独立

建议流程：

```text
用户消息
↓
基础预处理
├─ OCR
├─ 会话历史
└─ 当前 profile
↓
Level Classifier（仅在需要时）
↓
更新 profile/temporary level
↓
RAG 检索
↓
拼接主 Prompt
↓
主回答模型
↓
JOKE6 / 选项解析 / 入库
```

水平判定器只输出结构化数据，不输出面向用户的正文。

---

## 5. 为什么不建议让主模型一边回答一边画像

风险：

- 画像 metadata 可能泄露到正文
- Prompt 更复杂
- 主模型本身 temperature 较高，人格输出会影响分类稳定性
- 难测试
- 难单独调整判定规则
- 用户水平逻辑与诊断逻辑纠缠

小范围产品可以用轻量额外调用换取稳定性。

---

## 6. Level Classifier 输出建议

```json
{
  "profiling_valid": true,
  "level_vote": "advanced",
  "strength": 3,
  "evidence_type": [
    "diagnostic_reasoning",
    "operation_independence"
  ],
  "copy_risk": false,
  "reason": "用户主动做了安全模式对照，并据结果缩小驱动方向"
}
```

分类器禁止：

- 面向用户说话
- 给维修建议
- 修改 response_style
- 推断年龄/职业等无关信息
- 因单个术语直接判高手

---

## 7. Prompt 组装示意

伪结构：

```text
[SYSTEM - BASE]
FixPilot 身份、能力边界、格式铁律

[SYSTEM - DIAGNOSTIC]
问诊规则、D0-D4、一次一个关键问题

[SYSTEM - SAFETY]
R0-R3、数据保护、停止指导

[SYSTEM - PROFILE]
当前用户技术水平、来源、语气偏好

[SYSTEM - STYLE]
normal / roast / concise 的具体要求

[SYSTEM - KNOWLEDGE]
本轮 RAG 命中内容

[HISTORY]
当前会话历史

[USER]
本轮用户消息 / OCR 文字
```

现有工程若更适合把 RAG 放在最后一条 user 前，可以保持当前编排，只需要明确层级语义。

---

## 8. 不建议写进永久 System Prompt 的内容

以下属于动态状态，不应硬编码：

- 用户当前 level
- confidence
- 当前 response_style
- 当前诊断假设
- 本轮 RAG 内容
- 当前是否提示过画像
- 当前有效画像轮数

---

## 9. 诊断状态要不要单独保存

v1 不建议马上做复杂状态机数据库。

优先使用：

- 当前会话历史
- 简单内部 metadata（如果实现方便）

未来出现以下问题时再持久化：

- 模型频繁忘记当前假设
- 长会话上下文太大
- 需要统计排障路径
- 需要恢复中断会话状态

---

## 10. 兼容现有 JOKE6

JOKE6 仍由主回答输出标记。

但触发规则应来自 Style + Base：

```text
事实确认低级乌龙
AND
允许毒舌
AND
当前不是高风险/焦虑场景
```

不要由 Level Classifier 负责。

---

## 11. 兼容现有 OCR

OCR 是预处理，不属于“模型视觉”。

主 Prompt 必须持续明确：

```text
图片信息来源仅为 OCR 提取文字。
不得声称看到了图片中的颜色、外观、接线、位置关系。
```

---

## 12. 兼容现有 RAG

RAG 是知识来源，不是诊断结论。

主模型必须区分：

```text
知识库说某类问题通常如何
```

和：

```text
这个用户当前机器已经被证实是什么问题
```

二者不能混为一谈。

---

## 13. 版本管理建议

每份规则单独版本：

```text
base_policy_version
diagnostic_policy_version
safety_policy_version
profile_policy_version
style_policy_version
```

小项目阶段无需做配置中心，只要文件/常量按模块拆开即可。

---

## 14. 一句话产品原则

> **Prompt 可以最终拼成一段，但产品规则不应该只存在于一段 Prompt 里。**
