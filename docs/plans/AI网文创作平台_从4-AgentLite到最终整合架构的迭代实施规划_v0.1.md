---
title: AI网文创作平台 · 从 4-Agent Lite 到最终整合架构的迭代实施规划
type: roadmap
version: 0.1
date: 2026-04-09
status: planning
source:
  - C:\Users\Administrator\Documents\AI写小说开源项目调研与整合架构设计.md
  - C:\Users\Administrator\Documents\小说架构调研与对比.md
  - C:\Users\Administrator\Documents\AI网文创作平台_v0.2_推荐架构设计.md
  - C:\Users\Administrator\Documents\AI网文创作平台_PRD_4-Agent轻量版_v0.2.md
  - C:\Users\Administrator\Documents\AI网文创作平台_PRD_10-Agent整合版_v0.1.md
---

# AI网文创作平台 · 从 4-Agent Lite 到最终整合架构的迭代实施规划

## 1. 规划目标

这份规划回答的不是“下一步写什么代码”，而是：

> 如何从当前已经明确的 `4-Agent Lite v0.2.3`，稳态迭代到最终想要的整合架构，同时持续吸收参考项目的优点，而不是一次性重做。

本规划默认：

- 当前推荐基线不变，仍是 `4-Agent Lite`
- 最终目标不变，仍是“统一状态核心 + 人机协同 + 多 Agent 自动流水线”
- 迭代方式采用“先闭环、再韧性、后平台化”

---

## 2. 终局架构长什么样

最终整合架构可以概括成六层：

### 2.1 交互层

- Web 工作台
- CLI
- IDE 插件入口
- Dashboard / 追读力看板

### 2.2 编排层

- 轻量 Orchestrator
- 状态机校验
- warning 聚合与分级
- correlation_id 全链路透传

### 2.3 创作执行层

- 4-agent 主链路
- local rewrite fast-track
- 逐步扩展到 10-agent 自动流水线

### 2.4 状态核心层

- Story State Core
- versioned canonical store
- event semantics
- optimistic lock

### 2.5 检索与装配层

- timeline recall
- vector recall
- BM25 fallback
- rerank
- @DSL resolver
- prompt assembler

### 2.6 评估与治理层

- consistency review
- 追读力指标
- anti-AI-tone
- retrieval quality eval
- prompt regression
- golden chapter snapshots
- token / latency / budget governance

---

## 3. 迭代原则

1. 不牺牲当前闭环可用性去换未来想象空间。
2. 每次升级只引入一个新的核心复杂度来源。
3. 任何新自动化能力都必须同时补：
   - 可观测性
   - 可回归测试
   - 用户可解释性
4. 任何新状态写入路径都必须同时补：
   - 并发保护
   - 审计信息
   - 回滚或最小可追溯能力
5. 任何“看起来高级”的能力，如果当前没有明确用户价值和验收方式，一律延后。

---

## 4. 迭代总路线

总体路线分五段：

1. `Phase A`
   - 跑通当前 `4-Agent Lite v0.2.3`
   - 做到能写、能改、能审、能回写

2. `Phase B`
   - 补工程韧性
   - 解决可观测性、并发保护、质量基线

3. `Phase C`
   - 补写作智能
   - 让 review / rewrite / 追读力 / DSL 更像真正的网文工作流

4. `Phase D`
   - 平台化扩展
   - 从 4-agent 扩展到更多分工角色

5. `Phase E`
   - 最终整合架构
   - 多入口、多模式、多 agent、可观测、可持续运营

---

## 5. Phase A：4-Agent Lite 落地

### 5.1 目标

把当前 `v0.2.3` 真正做出来，形成第一个可用闭环。

### 5.2 范围

- monorepo 基础结构
- versioned schema
- canonical state core
- event log 基础版
- retrieval rules
- prompt assembler
- Planner / Writer / Reviewer / Committer
- local rewrite fast-track
- hook debt panel
- DSL warning panel
- minimum regression harness

### 5.3 这阶段吸收了哪些项目优点

- InkOS：状态核心、Hook 债务、审校意识
- AI_NovelGenerator：分步可控
- webnovel-writer：追读力方法、RAG
- NovelForge：Schema、@DSL、工作台感

### 5.4 阶段验收标准

- 能稳定创建项目并初始化章节状态
- 能生成整章草稿
- 能做局部改写且不越界污染上下文
- 能对 unresolved DSL 做端到端警告
- 能在确认后把 diff 回写到 Story State Core
- 能跑最小回归集

### 5.5 不允许在这阶段做的事

- 直接上 10-agent
- 提前引入重图数据库依赖
- 提前做复杂多端协作
- 把 Truth Files 重新变成主存储

---

## 6. Phase B：工程韧性升级

### 6.1 目标

让系统从“能跑”升级到“能持续迭代而不失控”。

### 6.2 优先补的 5 项

1. `事件语义标准化`
   - event_type
   - actor_type
   - correlation_id
   - causation_id

2. `并发保护`
   - chapter/state version
   - optimistic lock
   - PATCH compare guard

3. `检索质量基线`
   - Recall@K
   - DSL 命中率
   - 关键信息保留率

4. `Truth File 一致性标识`
   - projection_time
   - source_state_version
   - freshness hint

5. `轻量 Orchestrator`
   - warning 聚合
   - 流程链路 ID 透传
   - 状态机迁移合法性检查

### 6.3 阶段验收标准

- 任意一次章节生成都有完整链路事件
- 多端或重复提交不会静默覆盖状态
- retrieval 调整能被离线评估发现退化
- UI 能告诉用户当前 Truth File 是否滞后

### 6.4 为什么这阶段重要

这是从 `v1 可用` 迈向 `v1.5 可持续` 的关键。

如果跳过这一段，后面无论加多少 agent，复杂度都会放大失控。

---

## 7. Phase C：写作智能升级

### 7.1 目标

让系统更像真正的中文网文创作工作流，而不是技术上能跑的生成器。

### 7.2 优先补的能力

1. `DSL warning 分级`
   - block / warn / info

2. `Reviewer -> patch_plan`
   - target_span
   - severity
   - suggested_action
   - 让 local rewrite 直接消费

3. `追读力深入接入`
   - Planner 使用追读力信号
   - Reviewer 输出更明确的补强建议
   - Rewrite 接收 hook / payoff / tension 目标

4. `genre-aware anti-AI-tone`
   - 按题材配置容忍度
   - 区分仙侠、都市、历史等语言基线

5. `写作风格与卡片策略库`
   - 常用桥段卡片
   - 风格 profile
   - 题材包

### 7.3 阶段验收标准

- reviewer 输出不再只是建议列表，而是可执行修订计划
- local rewrite 可以直接消费 patch_plan
- anti-AI-tone 在不同题材下误判明显下降
- 用户能明显感觉到“更懂网文，而不只是更会写句子”

---

## 8. Phase D：平台化扩展到多 Agent

### 8.1 目标

在保持状态底座稳定的前提下，把 4-agent 扩展到更高自动化形态。

### 8.2 扩展顺序建议

不要一次性从 4 跳到 10。  
建议按职责逐步拆出：

1. `Composer`
   - 从 Planner / Prompt Assembler 中拆出上下文装配职责

2. `Observer + Reflector`
   - 从 Committer 前拆出事实提取和 delta 结构化职责

3. `Auditor`
   - 从 Reviewer 中拆出独立审计角色

4. `Reviser`
   - 从 local rewrite / reviewer patch_plan 升级成自动返修

5. `Architect / Normalizer / Radar`
   - 作为后续高自动化增强

### 8.3 这一阶段的关键前提

只有在以下条件满足时才应该扩：

- 事件语义标准化已完成
- optimistic lock 已完成
- retrieval 质量基线已建立
- regression harness 稳定运行
- 4-agent 闭环已经有真实使用反馈

### 8.4 阶段验收标准

- 每新增一个角色都能说清楚“比之前多解决了什么”
- agent 之间的 I/O 契约清楚
- 自动返修不会破坏状态一致性
- 多 agent 链路仍然可观测、可恢复

---

## 9. Phase E：最终整合架构

### 9.1 目标

形成你真正想要的平台：

- 人主导时，像专业小说 IDE
- 自动化时，像可审计的多 Agent 写作工厂
- 方法论上，真正吸收中文网文写法
- 工程上，可测试、可观测、可回归、可协作

### 9.2 最终形态应具备的能力

1. `多入口`
   - Web
   - CLI
   - IDE plugin

2. `双模式`
   - Manual-first workspace
   - Auto pipeline

3. `统一状态`
   - Story State Core
   - truth projections
   - event semantics

4. `多 Agent 平台化`
   - 4-agent 日常链路
   - 10-agent 高自动化链路

5. `方法论内化`
   - Hook debt
   - payoff balance
   - cool point / novelty
   - anti-AI-tone
   - 题材包 / 风格包 / 审校包

6. `工程治理`
   - regression
   - golden chapters
   - observability
   - budget / fallback
   - permission / audit

---

## 10. 每阶段应该吸收哪些项目的优点

| 阶段 | 重点吸收来源 | 吸收内容 |
|---|---|---|
| Phase A | InkOS + webnovel-writer + NovelForge | 状态核心、Hook 债务、RAG、Schema、@DSL |
| Phase B | InkOS + 平台工程思路 | 事件链路、审计、并发保护、观察能力 |
| Phase C | webnovel-writer + InkOS | 追读力、中文写法、anti-AI-tone、修订策略 |
| Phase D | InkOS + NovelForge | 多 agent 分工、上下文编排、结构化中间产物 |
| Phase E | 四者整合 | 平台化、低门槛、结构化控制、自动化上限 |

---

## 11. 推荐的实施节奏

### 短期

先把 `Phase A` 真做完，并以真实章节闭环作为首要目标。

### 中期

马上进入 `Phase B`，因为没有工程韧性，后续所有增强都会变成风险放大器。

### 中长期

在 `Phase B` 稳住之后，按 `Phase C -> Phase D -> Phase E` 推进。

不要反过来先做大量 agent 和平台功能，再回头补底层治理。

---

## 12. 在别的 IDE 里实施时的直接执行建议

如果换到别的 IDE，这样推进最稳：

1. 先读 `项目上下文总览与实施交接包`
2. 再读 `4-Agent Lite v0.2.3` 实施计划
3. 先完成 `Phase A`
4. 不要一开始实现 `10-agent`
5. 在 `Phase A` 接近完成时，同时准备 `Phase B` 的设计稿

如果需要参考项目代码：

- 建议下载到本地 `references/` 目录
- 只借鉴结构和模式，不直接复制实现
- 每次实现都写清“这一步参考了谁的什么优点”

---

## 13. 最终判断

这条路线的关键不是“尽快做成最终形态”，而是：

> 每一阶段都要留下一个可运行、可解释、可验证、可继续演进的稳定基线。

当前稳定基线是 `4-Agent Lite v0.2.3`。  
最终整合架构不是替代它，而是分阶段长出来。

所以整个项目的正确实施逻辑是：

`先闭环 -> 再韧性 -> 后写作智能 -> 再平台化 -> 最终整合架构`

