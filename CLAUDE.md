# CLAUDE.md

AI 网文创作平台开发指南

---

## 项目定位

这是一个面向中文网文长篇创作的 AI 写作平台，核心是：

> 以统一状态核心为底座、兼具人主导精修能力与多 Agent 自动流水线能力的创作平台。

**不是**"全自动写一本书"，**而是**帮助作者在长篇创作中稳定完成"查状态 → 写章节 → 精修 → 审查 → 回写"的闭环。

---

## 核心原则

1. **Story State Core 是唯一真相源** — 所有状态变更都通过它
2. **Truth Files 只是投影** — 不是主存储，只用于展示和上下文
3. **Manual-first, Auto-light** — 第一阶段以人主导为主，自动化为辅
4. **4-Agent 轻量闭环** — Planner → Writer → Reviewer → Committer
5. **局部改写快车道** — 高频精修必须有独立路径
6. **文档优先于代码** — 先读 docs/，再看 references/，最后写代码

docs/solutions/  # 已解决的已知问题（bug 修复、最佳实践、工作流决策），按 category 组织，YAML frontmatter 标记 module/tags/problem_type。实现功能或调试前先查这里

---

## 技能路由规则

本项目使用 gstack 和 compound-engineering (CE) 两套技能体系协同工作。

### 何时使用 gstack 技能

**产品与战略层面**：
- 产品想法、"这个值得做吗"、头脑风暴 → `/office-hours`
- 周复盘、工作模式回顾 → `/retro`
- 系统稳定性、安全审计 → `/cso`

**交付与质量保证**：
- 发布前审查、自动修 bug → `/review`
- 真实浏览器自动化测试、自动修 bug + 回归测试 → `/qa`
- 合入主干、跑测试、开 PR → `/ship`
- 发布后文档更新 → `/document-release`

**设计与用户体验**：
- 设计系统、品牌 → `/design-consultation`
- 视觉审计、设计打磨 → `/design-review`

**调试与问题定位**：
- Bug、错误、"为什么坏了"、500 错误 → `/investigate`

### 何时使用 compound-engineering (CE) 技能

**规划与设计阶段**：
- 需求探索、交互式细化想法 → `/ce:brainstorm`
- 结构化实施计划、带置信度检查 → `/ce:plan`
- 或使用一键审查管道 → `/ce:autoplan`（跑 CEO→设计→工程→DX 审查）

**执行阶段**：
- 执行计划、worktree + 任务追踪 → `/ce:work`

**审查阶段**：
- 多角色深度审查（50+ 专家 agent） → `/ce:review`

**知识沉淀**：
- 提炼学习成果、让下轮工作更轻松 → `/ce:compound`
- 迭代优化已有实现 → `/ce:optimize`

### 推荐组合流程

```
1. /office-hours (gstack)     ← 产品质询，想清楚到底在做什么
2. /ce:brainstorm (CE)        ← 需求探索，交互式把想法磨细
3. /ce:plan (CE)              ← 结构化实施计划，带置信度检查
   或 /autoplan (gstack)      ← 一键跑 CEO→设计→工程→DX 审查
4. /ce:work (CE)              ← 执行计划，worktree + 任务追踪
5. /review (gstack)           ← 发布前审查，自动修明显 bug
6. /ce:review (CE)            ← 多角色深度审查，50+ 专家 agent
7. /qa (gstack)               ← 真实浏览器自动化测试，自动修 bug + 回归测试
8. /ship (gstack)             ← 合入主干，跑测试，开 PR
9. /ce:compound (CE)          ← 提炼学习成果，让下轮工作更轻松
10. /retro (gstack)           ← 周复盘
```

### 核心互补点

- **gstack** 有真实浏览器（/browse, /qa）和安全审计（/cso），CE 没有
- **CE** 有知识复利（/ce:compound）和迭代优化（/ce:optimize），gstack 没有
- 两者都强调 plan before code，但 gstack 偏产品判断，CE 偏工程结构
- gstack 的 /qa 能自动修 bug + 生成回归测试，适合交付前最后把关
- CE 的 /ce:review 多人审查管道更细，适合复杂的架构决策

---

## 开发工作流

### 启动新功能

1. **先读文档**：
   - `docs/context/` — 项目上下文总览
   - `docs/prd/` — 产品需求文档
   - `docs/plans/` — 实施计划

2. **理解架构**：
   - 当前阶段：4-Agent Lite v0.2.3
   - 核心模块：Story State Core、4 个 Agent、检索层、评估层
   - 参考项目：InkOS、AI_NovelGenerator、webnovel-writer、NovelForge

3. **选择技能路径**：
   - 如果是新功能设计 → `/office-hours` 或 `/ce:brainstorm`
   - 如果是实施计划 → `/ce:plan` 或 `/autoplan`
   - 如果是执行开发 → `/ce:work`
   - 如果是审查代码 → `/review` 或 `/ce:review`
   - 如果是测试 → `/qa`

### 代码实施守则

1. **先读文档，再看参考仓库，再写代码**
2. **参考项目只学结构和模式，不直接搬实现**
3. **任何新模块都要回答三个问题**：
   - 它解决什么问题？
   - 它对应哪个已确认架构层？
   - 它为什么现在就该做，而不是下一阶段？
4. **任何新增自动化能力都不能破坏状态可解释性**
5. **任何新增 DSL / retrieval / review 规则，都要配回归测试**
6. **如果开始出现"概念很多但闭环跑不通"，优先回到 4-agent lite 最小链路**

### 测试与质量

- 使用 `/qa` 进行真实浏览器自动化测试
- 使用 `/review` 进行发布前代码审查
- 使用 `/ce:review` 进行深度架构审查
- 每次 prompt 或流程改动后，都要跑最小回归集

### 发布流程

1. `/review` — 发布前审查
2. `/qa` — 自动化测试
3. `/ship` — 合入主干、开 PR
4. `/document-release` — 更新文档

---

## 参考项目管理

参考项目位于 `references/repos/`，包括：

- **InkOS** — 状态精度、Truth Files、Hook 治理、多 Agent 自动化
- **AI_NovelGenerator** — 低门槛、分步可控、本地友好
- **webnovel-writer** — 中文网文方法论、追读力系统、RAG 双路召回
- **NovelForge** — Schema 驱动、@DSL 精确引用、卡片式 IDE 交互

**使用原则**：
- 只学结构和模式，不直接复制实现
- 学习沉淀记录在 `references/notes/`
- 实现时明确标注"参考了哪个项目的什么优点"

---

## 当前阶段重点

### Phase A：4-Agent Lite 落地（当前）

**目标**：把 v0.2.3 真正做出来，形成第一个可用闭环

**范围**：
- monorepo 基础结构
- Story State Core
- 4 个 Agent（Planner/Writer/Reviewer/Committer）
- 局部改写快车道
- 最小回归测试

**验收标准**：
- 能稳定创建项目并初始化章节状态
- 能生成整章草稿
- 能做局部改写且不越界污染上下文
- 能在确认后把 diff 回写到 Story State Core
- 能跑最小回归集

### 不允许在这阶段做的事

- 直接上 10-agent
- 提前引入重图数据库依赖
- 提前做复杂多端协作
- 把 Truth Files 重新变成主存储

---

## 技术栈

- **前端**：Vue 3, TypeScript, Element Plus
- **后端**：FastAPI, Python 3.11
- **数据库**：SQLite（Story State Core）
- **ORM**：SQLModel
- **LLM**：LiteLLM（支持多模型路由）
- **检索**：本地 vector store + BM25
- **测试**：pytest, Playwright, Vitest
- **模板**：Jinja
- **包管理**：pnpm workspace

---

## 关键概念

### Story State Core

唯一真相源，至少覆盖：
- characters（角色状态）
- relationships（关系状态）
- plot progress（主线/支线进度）
- hook debt（伏笔债务）
- resource ledger（资源账本）
- chapter summaries（章节摘要）
- style profile（风格约束）
- card usage（卡片使用记录）

### Truth Files

非常重要，但不是主存储。正确定位：
- 给人看
- 给模型读
- 做导出
- 做投影视图

### 4-Agent 闭环

- **Planner** — 规划章节目标、节奏、卡片
- **Writer** — 生成草稿
- **Reviewer** — 审查一致性、追读力、风格
- **Committer** — 回写状态变更

### 局部改写快车道

高频主功能，必须单独成链路：
```
selected text → local context assemble → local write → diff validate → commit preview
```

---

## 常见问题

### Q: 为什么不直接做 10-agent？

A: 4-agent 不是缩水版，而是当前推荐实施基线。10-agent 是后续平台化增强形态。先把轻量闭环跑稳，再扩展。

### Q: 为什么 Truth Files 不是主存储？

A: Truth Files 是投影视图，方便人和模型阅读。主存储是 Story State Core，保证状态一致性和可审计性。

### Q: 如何避免 AI 腔？

A: 通过 anti-AI-tone 软评分、题材包、风格约束、Reviewer 审查等多层机制。不做简单硬门槛。

### Q: 如何保证长篇一致性？

A: 通过 Story State Core 维护角色、关系、资源、伏笔等状态，检索层按需装配上下文，Reviewer 审查一致性。

---

## 更新日志

- 2026-04-14：初始版本，定义项目定位、技能路由、开发工作流
