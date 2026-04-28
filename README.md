---
title: AI 网文创作平台
type: release-readme
status: active
updated: 2026-04-28
---

# AI 网文创作平台

一个面向长篇网文生产的多 Agent 创作系统。当前版本已经完成 Phase A 收口：具备可运行的 4-Agent 主链路、局部改写能力、状态管理、HTTP API 和最小回归测试框架。

## 当前功能

### 1. 4-Agent 主创作链路

已实现以下核心角色：

- `Planner`：生成章节规划和节拍
- `Writer`：基于章节目标生成草稿
- `Reviewer`：对草稿做一致性与可读性审查
- `Committer`：将确认后的结果回写到状态核心

当前主流程已经可以跑通：

`规划 -> 写作 -> 审查 -> 回写`

### 2. Story State Core

项目使用 `Story State Core` 作为唯一状态真相源，负责保存：

- 项目状态
- 章节状态
- 版本号
- 提交预览
- 运行事件

当前已接入 SQLite 和 repository 层，支持章节状态读取、更新与基础版本保护。

### 3. 局部改写快车道

除了整章生成外，项目还支持 `local rewrite` 路径，用于：

- 对选中段落做局部改写
- 控制改写边界
- 返回 diff 结果，避免整章重写

这条链路已经有独立 API 和测试覆盖。

### 4. FastAPI 接口

当前已暴露最小可用的 HTTP 接口，包括：

- 项目读取接口
- 章节状态读取 / 更新接口
- 主 Agent 流程接口
- 局部改写接口
- 事件查询相关接口

这使项目已经从纯 CLI 验证阶段进入“可被外部工作台或前端调用”的阶段。

### 5. Schema 与测试

当前仓库已经具备：

- Agent I/O JSON Schema
- 章节状态 Schema
- 主流程与局部改写测试
- API 路由测试
- 最小回归测试集

现阶段测试覆盖的重点是“主链路是否可跑通”和“状态更新是否安全”，而不是 UI 展示。

## 当前仓库结构

```text
apps/web/         Web 端工作台（预留/逐步补全）
docs/             设计、计划和阶段文档
evals/            最小回归与评测脚本
packages/         Agent 与 Contract
prompts/          Prompt 相关资源
references/       参考资料
services/api/     FastAPI 服务
src/              预留扩展代码
tests/            集成、API、Agent、evals 测试
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- pnpm

### 安装依赖

```bash
pip install -e .
```

### 运行测试

```bash
make test
```

或直接运行：

```bash
pytest -v
```

### 启动 API

```bash
uvicorn services.api.app.main:app --reload
```

## 当前阶段状态

### 已完成

- 4-Agent 闭环
- local rewrite 独立链路
- Story State Core + SQLite
- FastAPI 路由层
- 最小回归工具
- Agent Contract / Schema
- 基础测试框架

### 暂未完成

- 完整前端工作台
- 检索层增强（向量检索 / DSL / rerank）
- 更细粒度的事件语义
- 更强的网文专项评分能力

## 下一步迭代计划

### Phase B

下一阶段的重点不是继续堆功能，而是把现有链路变得更稳、更可评估：

1. **并发保护补齐**
   - 完整收口 optimistic concurrency
   - 防止章节状态被静默覆盖

2. **事件语义标准化**
   - 为每次运行补齐 correlation_id 等关键字段
   - 让主流程更容易调试、追踪和复盘

3. **最简检索接入**
   - 从 Story State Core 中拉取最近章节摘要
   - 为 Writer 提供更稳定的上下文

4. **检索质量基线**
   - 为上下文召回建立离线评测
   - 让后续检索优化有明确退化监控

5. **Truth File 一致性标识**
   - 标记投影视图是否滞后于最新状态
   - 避免用户误读旧内容

### Phase C

在 Phase B 稳定后，项目会进入写作智能升级阶段，重点包括：

- DSL 引用与 warning 分级
- Reviewer 输出可执行 patch plan
- 追读力信号更深接入
- 按题材做 anti-AI-tone 校准
- 更贴近网文生产的风格与卡片策略能力

## 仓库状态说明

当前仓库处于“Phase A 已完成、Phase B 准备展开”的阶段。它已经不是概念设计或纯文档项目，而是一个具备主链路、接口、状态核心和测试基础的可运行原型。
