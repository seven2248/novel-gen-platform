# Phase A 收口后工作规划

> **状态**: planning
> **创建日期**: 2026-04-16
> **依赖前置**: Phase A Gap Closeout (2026-04-16-phase-a-gap-closeout.md) 完成
> **范围**: W17 ~ W21+，覆盖 Phase B 全程、过渡期、Phase C 起手

---

## 1. Phase A 收口后的真实起点

### 已落地（截至 W16 收口）

- 4-Agent 闭环（Planner → Writer → Reviewer → Committer），CLI 入口，Ollama 本地跑通
- 局部改写快车道（local rewrite），独立链路
- Story State Core + SQLite，基础 repository
- 28 个测试全过（agent + CLI + fallback + schema）
- prompt 外置化（templates/ + fallback 到内联）
- 代码审查一轮 P0/P1/P2 全修
- FastAPI 路由层（State API + Agent Run API + Local Rewrite API）
- 最小回归工具（3-case YAML suite + story_constraints scorer）
- 收口文档

### 明确没做

- Vue workspace shell（降级为可选，不阻塞 Phase A 收口）
- 事件语义标准化
- 检索层（retrieval rules / DSL / vector store）
- 追读力深度接入
- anti-AI-tone 按题材校准

### Phase A 验收标准达成情况

| 验收标准 | 状态 |
|----------|------|
| 能稳定创建项目并初始化章节状态 | 已达成 |
| 能生成整章草稿 | 已达成 |
| 能做局部改写且不越界污染上下文 | 已达成 |
| 能在确认后把 diff 回写到 Story State Core | 已达成 |
| 能跑最小回归集 | 已达成 |

---

## 2. W17：Phase B 起手（下周）

目标：挑最能降低后续风险的 4 件事先做，把 Phase A 的松动件收紧。

### 2.1 环境同步 + 本地回归基线（半天）

**问题**：pyproject.toml 声明了 fastapi/uvicorn，但环境里没装。测试全靠手动逐条跑，没有一键入口。

**做什么**：
- `pip install -e .` 跑通全部已声明依赖
- 补 `pyyaml>=6.0.2` 到 pyproject.toml
- 确认 httpx 是否跟着 fastapi 装进来，没有再单列
- 写一个 Makefile 或等价脚本，`make test` 一键跑 pytest 全量
- 验证：`make test` 一次通过，无需手动补依赖

**不做什么**：
- 本轮不搭 GitHub Actions 或等价 CI 流水线（如后续需要可单独安排）

**为什么现在做**：后面 Phase B 的每个改动都需要回归保护。没有本地一键回归入口，回归工具形同虚设。

### 2.2 并发保护（1-2 天）

**问题**：Task 1 已经在 API 层加了 409 version conflict 返回，但底层 `StoryStateRepository` 的 optimistic lock 还不完整。

**做什么**：
- 核查现有 `chapter_state` 表和 `StoryStateRepository` 中 version 字段与 compare-and-swap 逻辑的实现程度
- 补齐缺失部分：确保 `update_chapter_state()` 走真正的 `WHERE version = expected_version`（不只是 API 层返回 409，底层也要拦）
- 补 2-3 个并发写入测试（同一章节两个并发 PATCH）
- 确保 CLI 路径和 API 路径都走同一套 version guard

**不做什么**：
- 不做分布式锁
- 不做 multi-writer 仲裁

**为什么现在做**：这是整个状态核心的安全底线。没有它，后续任何多 agent 或多入口的扩展都会静默覆盖状态。Task 1 已经把 API 接口设计好了（409 返回），底层逻辑补上就闭环。

### 2.3 事件语义基础版（1 天）

**问题**：目前没有任何运行记录，调试"这次生成出了什么问题"完全靠日志翻找。

**做什么**：
- 核查现有 `EventLog` 模型已有哪些字段，确认 `event_type`、`actor_type`、`correlation_id` 的缺失项
- 补齐缺失字段，对已有字段做语义标准化（统一枚举值、字段命名）
- 主链路（`run_main_flow`）每次执行写一条 event（如已有写入逻辑，收紧为标准格式）
- 一个查询接口 `GET /events?correlation_id=xxx`
- 补 2 个测试：event 写入结构正确、按 correlation_id 查询返回正确

**不做什么**：
- 不做 causation_id 链（Phase B 后半段）
- 不做 event replay
- 不做 warning 聚合

**为什么现在做**：有了 correlation_id，后续调试就有了抓手。没有它，Phase C 的 reviewer patch_plan 和 Phase D 的多 agent 链路都没法做可观测。

### 2.4 最简检索（1 天）

**问题**：Phase A 跳过了检索层。v0.2.3 计划里有 retrieval rules 和 prompt assembler，但实际代码里还没实现。W18 要评检索质量之前必须先有东西可评。

**做什么**：
- 从 Story State Core 里按 chapter_id 拉最近 N 章摘要（SQL 查询）
- 拼进 writer prompt 的 context 区块
- 补 1-2 个测试：检索返回正确章节数、context 区块格式正确

**不做什么**：
- 不上向量数据库
- 不上 BM25
- 不做 @DSL 解析
- 不做 rerank

**为什么现在做**：检索提前到 W17，W18 就能直接上检索质量基线（Recall@K 等），不用再补前置。

---

## 3. W18：Phase B 核心

### 3.1 检索质量基线

**前置**：W17 最简检索已就位。

**做什么**：
- 定义 Recall@K 指标：给定一个章节目标，检索返回的上下文是否覆盖了必要的角色/关系/伏笔信息
- 在 evals/ 下新增 retrieval 评估 case（3-5 个）
- 角色与伏笔信息保留率：摘要是否丢失了影响后续剧情的关键角色状态或未兑现伏笔
- 关键信息保留率：摘要是否丢失了影响后续剧情的关键信息

**不做什么**：
- 不做自动化的检索调参
- 不做 A/B 检索策略对比
- 不评 DSL 命中率（@DSL 解析尚未实现，待 Phase C DSL resolver 落地后再单列此指标）

### 3.2 Truth File 一致性标识

**做什么**：
- Truth File 投影加 `projection_time`、`source_state_version` 两个元数据字段
- freshness hint：如果 Truth File 的 source_state_version 落后于当前 state version，标记为 stale
- 前端（未来 shell）或 CLI 能看到 "此文件可能不是最新" 的提示

---

## 4. W19：Phase B 收口

### 4.1 轻量 Orchestrator

**前置**：event 语义 + 并发保护都已就位。

**做什么**：
- 提取 `run_main_flow` 中隐含的编排逻辑到独立的 orchestrator 模块
- warning 聚合：收集各 agent 运行中的 warning，统一返回给调用方
- 状态机迁移合法性检查：章节不能从 `committed` 跳回 `drafting`，除非显式重置
- correlation_id 透传：orchestrator 生成 correlation_id，传给每一步

**不做什么**：
- 不做 workflow DSL
- 不做可配置的 agent 链路编排
- 不做失败重试策略

### 4.2 Phase B 验收

| 验收标准 | 来源 |
|----------|------|
| 任意一次章节生成都有完整链路事件 | 路线图 v0.1 §6.3 |
| 多端或重复提交不会静默覆盖状态 | 路线图 v0.1 §6.3 |
| retrieval 调整能被离线评估发现退化 | 路线图 v0.1 §6.3 |
| UI/CLI 能告诉用户当前 Truth File 是否滞后 | 路线图 v0.1 §6.3 |

---

## 5. W20：过渡期 — Vue Workspace Shell

### 为什么放在这里

Phase C 的核心价值是"让系统更像真正的网文工作流"，这个判断很难只靠 CLI 输出来做。一个能看到 review suggestions、hook debt、commit preview 的界面，哪怕很粗糙，也能帮更快判断 Phase C 的方向对不对。

### 做什么

- Vue 3 + Element Plus + Vite，最小 shell
- 三个区块：章节状态面板、审查建议面板、提交预览面板
- 接已有 API（此时 API 层已稳定 3 周）
- Vitest 组件测试

### 不做什么

- 不做全局状态管理（prop-driven 足够）
- 不做实时通信（WebSocket）
- 不做响应式适配

---

## 6. W21+：Phase C 起手 — 写作智能升级

### 优先补的能力（按顺序）

1. **DSL warning 分级**：block / warn / info，让 @引用 的问题有轻重缓急
2. **Reviewer → patch_plan**：target_span + severity + suggested_action，让 local rewrite 直接消费审查结果
3. **追读力深入接入**：Planner 使用追读力信号、Reviewer 输出补强建议、Rewrite 接收 hook/payoff/tension 目标
4. **genre-aware anti-AI-tone**：按题材配置容忍度，区分仙侠、都市、历史等语言基线
5. **写作风格与卡片策略库**：常用桥段卡片、风格 profile、题材包

### Phase C 验收标准（来自路线图 v0.1 §7.3）

- reviewer 输出不再只是建议列表，而是可执行修订计划
- local rewrite 可以直接消费 patch_plan
- anti-AI-tone 在不同题材下误判明显下降
- 用户能明显感觉到"更懂网文，而不只是更会写句子"

---

## 7. 时间线总览

| 周次 | 聚焦 | 核心产出 |
|------|------|----------|
| W16（本周） | Phase A 收口 | API 路由 + 回归工具 + 收口文档 |
| W17 | Phase B 起手 | CI 基线 + 并发保护 + 事件语义 + 最简检索 |
| W18 | Phase B 核心 | 检索质量基线 + Truth File 一致性标识 |
| W19 | Phase B 收口 | 轻量 Orchestrator + Phase B 验收 |
| W20 | 过渡期 | Vue workspace shell（接已有 API） |
| W21+ | Phase C 起手 | DSL warning 分级 + reviewer patch_plan |

---

## 8. 关键决策记录

| 决策 | 结论 | 依据 |
|------|------|------|
| W17 优先级排序 | 环境同步 → 并发保护 → 事件语义 → 最简检索 | 用户确认 2026-04-16 |
| 最简检索时机 | W17（提前） | 提前到 W17 让 W18 能直接上检索质量基线 |
| Vue shell 时机 | W20（Phase B 收口后、Phase C 之前） | 为 Phase C 写作智能提供可视化验证界面 |
| Task 4 (Vue shell) 在 Phase A 中的定位 | 降级为可选，不阻塞收口 | Phase A 验收标准中没有 Web shell 要求，同事 review 确认 |
| Phase A API 路由测试 LLM mock | 必须显式补 | tests/agents/conftest.py 的 autouse mock 不覆盖 tests/api/ |

---

## 9. 风险与注意事项

1. **检索层的真实复杂度**：W17 的最简检索是 SQL 查 N 章摘要，但 Phase C 需要向量检索 + BM25 + rerank。从 SQL 到 RAG 的跨度不小，W18 评完检索质量基线后需要判断是否要在 Phase B 内就引入向量存储。
2. **Ollama 模型能力瓶颈**：gemma4:26b 在 CoT reasoning 上吃 token 严重（需 max_tokens>=4096）。Phase C 的追读力和 anti-AI-tone 对模型能力要求更高，可能需要评估是否切换到更强的本地模型或回到 API。
3. **前端投入的回报周期**：W20 的 Vue shell 是一次性投入，但如果 Phase C 方向调整大，shell 可能需要重做。建议 shell 做得尽量薄，只渲染 API 返回的数据，不做前端逻辑。
