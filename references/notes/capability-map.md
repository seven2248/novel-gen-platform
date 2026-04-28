---
title: 参考能力映射
type: reference-note
status: draft
updated: 2026-04-09
---

# 参考能力映射

记录每个参考仓库最值得借鉴的能力，以及它在我方系统中的映射位置。

## AI-Novel-Writing-Assistant

- 借鉴点：
  - AI-native 工作台的产品包装
  - 自动导演开书的长链路组织
  - Creative Hub + Agent Runtime + 任务中心的统一入口感
  - 整本生产主链的连续表达
  - 检查点恢复、现有项目接管、状态可解释性
- 不借鉴点：
  - 不拿它定义我方 canonical story state
  - 不拿它定义中文网文追读力指标体系
  - 不拿它定义 Schema / @DSL 精确契约
  - 不沿用其完整产品边界和较重工程栈
- 我方落点模块：
  - `交互层`：Creative Hub、工作台、任务状态展示
  - `编排层`：阶段推进、checkpoint resume、任务流转
  - `创作执行层`：导演链路到章节执行链的组织方式
- 风险说明：
  - 产品边界偏大，容易诱导我方过早平台化
  - 技术栈更重，直接跟随会冲击当前轻量实施计划
  - 公开材料强调产品工作流多于状态精度，不适合作为状态核心主锚点

## 当前参考分工提醒

- InkOS：状态核心、Truth Files、Hook 治理、审计返修
- AI_NovelGenerator：低门槛、分步可控、本地友好
- webnovel-writer：中文网文方法论、追读力、RAG
- NovelForge：Schema、@DSL、结构化工作台
- AI-Novel-Writing-Assistant：产品化外壳、导演式主链、工作台整合
