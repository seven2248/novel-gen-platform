---
title: AI网文创作平台 · 项目上下文总览与实施交接包
type: context-pack
version: 0.1
date: 2026-04-09
status: ready-for-handoff
source:
  - C:\Users\Administrator\Documents\AI写小说开源项目调研与整合架构设计.md
  - C:\Users\Administrator\Documents\小说架构调研与对比.md
  - C:\Users\Administrator\Documents\AI网文创作平台_v0.2_推荐架构设计.md
  - C:\Users\Administrator\Documents\AI网文创作平台_PRD_4-Agent轻量版_v0.2.md
  - C:\Users\Administrator\Documents\AI网文创作平台_实施计划_4-Agent轻量版_v0.2.2.md
  - C:\Users\Administrator\Documents\AI网文创作平台_PRD_10-Agent整合版_v0.1.md
---

# AI网文创作平台 · 项目上下文总览与实施交接包

## 1. 这份文件的用途

这不是 PRD，也不是实施计划。

它的作用是让你在另一个 IDE 或新的 AI 会话里，能够在最短时间内理解：

1. 这个项目最终想做成什么。
2. 为什么当前不直接做最终形态。
3. 参考开源项目分别该吸收什么优点。
4. 我们已经达成了哪些明确共识。
5. 当前最适合继续推进的实施基线是什么。

如果新环境只能先读一个文件，先读这份。

---

## 2. 最终目标，一句话定义

目标不是做一个“会续写几章的 AI 写作工具”，而是做一个：

> 面向中文网文长篇创作的、以统一状态核心为底座、兼具人主导精修能力与多 Agent 自动流水线能力的创作平台。

它要同时吸收四类能力：

- `InkOS` 的状态精度、Truth Files、Hook 治理、多 Agent 自动化。
- `AI_NovelGenerator` 的低门槛、分步可控、本地友好。
- `webnovel-writer` 的中文网文方法论、追读力系统、RAG 双路召回。
- `NovelForge` 的 Schema 驱动、@DSL 精确引用、卡片式 IDE 交互。

最终形态不是四个项目拼一起，而是把它们的优点拆回不同层，再重新组合成一套一致的系统。

---

## 3. 两份调研文档给出的核心结论

两份调研最终都指向同一条主线：

### 3.1 行业主线已经变了

2024-2026 的小说/长文写作系统，关键不再是“更复杂的 prompt”，而是：

`State + Retrieval + Evaluation + Review Loop`

也就是：

- 用状态系统维护长篇一致性
- 用检索系统按需装配上下文
- 用评估系统防止质量漂移
- 用 review / revise 闭环替代一次性生成

### 3.2 开源项目的优点不在同一层，可以叠加

- InkOS 的强项在状态层和自动流水线。
- AI_NovelGenerator 的强项在交互门槛和分步控制。
- webnovel-writer 的强项在中文网文写法和追读力指标。
- NovelForge 的强项在结构化控制和 IDE 工作台。

所以正确的整合方式不是二选一，而是分层吸收。

### 3.3 当前最优路线不是“直接平台化”，而是“先收敛核心闭环”

已经验证过的结论是：

- 先做 `Story State Core`
- 先把 `Truth Files` 降为投影视图
- 先跑通 `4-agent` 轻量闭环
- 再往更强自动化和平台化升级

这条路线不是保守，而是避免过早进入高复杂度、低验证效率的陷阱。

---

## 4. 我们已经确认的最终方向

### 4.1 最终架构不是单一产品形态

最终整合架构应该有多层：

1. `交互层`
   - 章节工作台
   - Dashboard
   - CLI / IDE / Web 三端入口

2. `编排层`
   - 轻量 Orchestrator
   - 状态机迁移
   - warning 聚合
   - correlation_id 全链路透传

3. `创作执行层`
   - 4-agent 轻量闭环
   - 逐步扩展到 10-agent 自动流水线

4. `状态核心层`
   - Story State Core
   - Canonical store
   - Event log / 后续事件语义化

5. `检索与装配层`
   - timeline recall
   - vector recall
   - BM25 fallback
   - rerank
   - @DSL resolver
   - prompt assembler

6. `评估与治理层`
   - consistency review
   - 追读力指标
   - anti-AI-tone 软评分
   - regression harness
   - 预算与降级策略

### 4.2 当前不是最终形态，但当前路线是对的

当前最成熟、最适合实施的方案，是 `4-Agent Lite v0.2.2`。

原因：

- 它已经把最小闭环收敛清楚。
- 它已经解决了最危险的脏数据和静默失效问题。
- 它保留了未来向最终整合架构升级的接口。
- 它没有把系统拖进过早的平台化和重编排。

---

## 5. 必须吸收的开源项目优点

## 5.1 InkOS：应该吸收什么

要吸收的不是“10-agent 的名字”，而是它对长篇一致性的理解：

- Truth Files / 状态分层思路
- Hook debt / pending hooks
- 资源账本
- 章节摘要与状态变更
- 角色知识边界
- anti-AI-tone 意识
- 多 Agent 链路中的审计和返修思路

不要直接照搬的：

- 一上来全量复刻 10-agent
- 纯 CLI 导向
- 让系统在没有足够观察能力时全自动跑长链路

## 5.2 AI_NovelGenerator：应该吸收什么

- 低门槛
- GUI 分步操作
- 本地友好
- “先生成一步，再确认一步”的用户心智

不要直接照搬的：

- 旧 GUI 技术形态
- 把状态管理停留在单机工具级

## 5.3 webnovel-writer：应该吸收什么

- 中文网文写作方法论
- 追读力指标
- Hook / Cool point / 微兑现 / 债务追踪
- RAG 双路召回思路
- 写作过程中的预检和规则约束

不要直接照搬的：

- 强绑定 Claude Code 生态
- 把 Dashboard 只做成展示层而不参与决策

## 5.4 NovelForge：应该吸收什么

- Schema 驱动
- @DSL 精确引用
- 卡片式工作台
- 知识图谱思维
- review / save 的工作流感觉

不要直接照搬的：

- 过重的 IDE 化与图数据库前置依赖
- 一上来做太多复杂编排能力

---

## 6. 写作方法论层面必须保留的东西

这个项目不是“技术架构正确”就够了，必须保留网文创作的方法论。

这些是最终系统里必须长期存在的：

### 6.1 Hook Debt

- 已埋伏笔
- 预期回收章节
- 是否超期
- 当前章节是否触碰到某条未回收伏笔

### 6.2 追读力

至少保留以下四类指标：

- `hook_strength`
- `payoff_balance`
- `pace_tension`
- `novelty_density`

它们不能只出现在 Dashboard 上，必须进入 Planner / Reviewer / Rewriter 的决策。

### 6.3 中文写作约束

- 避免明显 AI 腔
- 控制疲劳词
- 控制套路重复
- 区分题材的语言容忍度

### 6.4 长篇一致性

- 角色状态不乱
- 关系不乱
- 资源账本不乱
- 知识边界不乱
- 设定不乱

这些能力最终都应该由 Story State Core 提供支撑，而不是依赖 prompt 记忆。

---

## 7. 当前已经确认的关键概念

### 7.1 Story State Core

这是唯一真相源。

它不是 Markdown 文档堆，也不是 UI 面板的集合，而是一个 canonical state system。

它至少应覆盖：

- characters
- relationships
- plot progress
- hook debt
- resource ledger
- chapter summaries
- style profile
- card usage

### 7.2 Truth Files

Truth Files 非常重要，但它们不是主存储。

正确定位：

- 给人看
- 给模型读
- 做导出
- 做投影视图

不正确定位：

- 当主数据库
- 当唯一写入目标

### 7.3 4-agent 与 10-agent 的关系

4-agent 不是缩水失败版，10-agent 也不是天然更高级。

更准确的关系是：

- `4-agent` 是当前推荐实施基线
- `10-agent` 是后续平台化增强形态

当前 4-agent：

- Planner
- Writer
- Reviewer
- Committer

最终 10-agent 方向可扩展为：

- Radar
- Planner
- Composer
- Architect
- Writer
- Observer
- Reflector
- Normalizer
- Auditor
- Reviser

### 7.4 Local Rewrite Fast-Track

局部改写不是边角功能，它是高频主功能。

必须单独成链路：

`selected text -> local context assemble -> local write -> diff validate -> commit preview`

它必须比整章生成更快、更可控、更可解释。

---

## 8. 当前已定下来的非谈判项

下面这些，默认不要在别的 IDE 里随意推翻：

1. `Story State Core` 是唯一真相源。
2. `Truth Files` 只做投影视图。
3. 第一阶段走 `Manual-first, Auto-light`。
4. 第一阶段以 `4-Agent Lite v0.2.2` 为实施基线。
5. 局部改写必须有独立快车道。
6. `@DSL` warning 必须端到端闭环。
7. commit preview 必须有 hash guard。
8. model routing 采用能力分层，不写死厂商。
9. anti-AI-tone 先做软评分，不做简单硬门槛。
10. 文档、PRD、实施计划优先于参考代码。

---

## 9. 当前实施基线：4-Agent Lite v0.2.2

如果在另一个 IDE 里直接开工，默认从这版实施计划出发。

它已经包含：

- monorepo 冷启动 Task 0
- versioned schema
- commit preview safety
- DSL safety
- model capability routing
- local rewrite out-of-scope guardrails
- minimum regression harness
- hook debt panel
- DSL warning panel
- warning override E2E

它的定位是：

> 做出第一个能稳定支撑长篇网文章节级创作闭环的工程底座。

---

## 10. 在别的 IDE 里实施时，推荐的阅读顺序

### 第一顺位

1. 这份上下文总览
2. `AI网文创作平台_实施计划_4-Agent轻量版_v0.2.2.md`

### 第二顺位

3. `AI网文创作平台_PRD_4-Agent轻量版_v0.2.md`
4. `AI网文创作平台_v0.2_推荐架构设计.md`

### 第三顺位

5. `AI写小说开源项目调研与整合架构设计.md`
6. `小说架构调研与对比.md`
7. `AI网文创作平台_PRD_10-Agent整合版_v0.1.md`

---

## 11. 在别的 IDE 里实施时的操作守则

1. 先读文档，再看参考仓库，再写代码。
2. 参考项目只学结构和模式，不直接搬实现。
3. 如果要 clone 参考仓库，单独放到 `references/` 目录，不混入主工程源码。
4. 任何新模块都要回答三个问题：
   - 它解决什么问题？
   - 它对应哪个已确认架构层？
   - 它为什么现在就该做，而不是下一阶段？
5. 任何新增自动化能力都不能破坏状态可解释性。
6. 任何新增 DSL / retrieval / review 规则，都要配回归测试。
7. 如果开始出现“概念很多但闭环跑不通”，优先回到 `4-agent lite` 最小链路。

---

## 12. 这一轮讨论最终沉淀出的核心判断

### 最重要的一句

这个项目的本质，不是“做一个会写小说的 AI”，而是：

> 做一个能长期稳定维护小说世界状态、并让人和 AI 共同推进长篇创作的工程系统。

### 当前阶段最重要的一句

不要跳过 `4-Agent Lite v0.2.2` 直接冲最终大一统平台。  
正确路线是：

> 先做出可验证、可回归、可解释、可持续迭代的轻量闭环，再扩成最终整合架构。

### 最终阶段最重要的一句

最终整合架构不是抛弃当前方案，而是：

> 在当前轻量闭环之上，补足工程韧性、可观测性、协作安全和多 Agent 平台化能力。

