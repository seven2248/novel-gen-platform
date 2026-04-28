---
title: "Prompt 外置化时机决策：验证轮次后再重构"
date: "2026-04-14"
category: docs/solutions/workflow-issues/
module: prompts
problem_type: workflow_issue
component: development_workflow
severity: medium
tags:
  - prompt-management
  - system-prompt
  - externalization
  - workflow-decision
  - gemma4
  - litellm
  - iterative-development
applies_when:
  - "换新模型（尤其是 CoT 推理模型）时"
  - "还在频繁调整 prompt 参数阶段"
  - "还没跑完一个完整的验证轮次"
---

# Prompt 外置化时机决策：验证轮次后再重构

## Context

小说项目 4-Agent 系统（Planner/Writer/Reviewer/Committer）当前状态：
- 系统提示词（`PLANNER_SYSTEM`、`WRITER_SYSTEM`、`REVIEWER_SYSTEM`）硬编码在 `.py` 文件中
- `base.py` 已预留 `load_prompt(name)` 接口，意图是从文件加载 prompt
- templates 目录不存在

面临决策：**现在就将 prompt 外置化，还是等模型行为验证稳定后再做？**

## Guidance

**决策：延迟 prompt 外置化，先用内联 prompt 跑通完整验证轮次。**

时序：
1. 先用内联 prompt 快速迭代调优（当前状态）
2. 跑通 W16 小说主线（多章节、局部改写各一圈）
3. 记录期间改过的 prompt 及改动原因
4. 回头做 prompt 外置化 + 菜单测试界面

## Why This Matters

**现在做的代价**：
- gemma4:26b 对齐风格未摸透，prompt 会大量改动
- 外置文件刚建立就频繁修改，维护成本高
- 等于对空气设计——你不知道最终需要什么结构

**以后做的代价**：
- 只需搬字符串 + 改加载逻辑，预计 2 小时
- 收益在验证后才明确：这时你知道哪些 prompt 要外露、要不要分组、要不要版本管理

**核心原则**：知识管理的"验证轮次"对应产品开发的"PMF"——没摸清之前不急着重构。

## When to Apply

- 换新模型（尤其是 CoT 推理模型）时
- 还在频繁调整 prompt 参数阶段
- 还没跑完一个完整的验证轮次
- Prompt 的稳定性还没被测试验证

## Examples

```
当前：PLANNER_SYSTEM = """..."""
  └── ❌ 现在外置 → prompt 频繁变 → 外置文件快速过时 → 维护负担

验证后：load_prompt("planner") → services/api/app/templates/planner.txt
  └── ✅ 模型行为稳定 → 外置一次到位 → 接口清晰 → 菜单可配置
```

## Implementation Path

Prompt 外置化涉及的工作：

1. 创建 `services/api/app/templates/` 目录
2. 4 个 `.txt` 文件：`planner_system.txt`、`writer_system.txt`、`reviewer_system.txt`、`committer_system.txt`
3. 修改 `base.py` 的 `load_prompt()`：优先读文件，不存在时 fallback 到代码内联值
4. Agent 文件中改为：`PLANNER_SYSTEM = load_prompt("planner_system") or DEFAULT_PLANNER_SYSTEM`
5. 菜单测试界面（后续 FastAPI 层实现）

## Related

- Bug fix: [gemma4-cot-json-output-2026-04-14.md]() — gemma4:26b CoT JSON 输出问题的修复
