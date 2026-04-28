---
title: "gemma4:26b CoT reasoning 导致 JSON 输出被截断"
date: "2026-04-14"
category: docs/solutions/logic-errors/
module: agents
problem_type: logic_error
component: tooling
severity: high
tags:
  - gemma4
  - ollama
  - litellm
  - cot
  - json-output
  - max-tokens
  - markdown-pollution
symptoms:
  - "gemma4:26b 输出 content 为空，reasoning 过程占据所有 token"
  - "max_tokens=50 时 json.loads() 解析返回空字典"
  - "模型在 JSON 外包裹 ```json ... ``` markdown 代码块"
root_cause: "gemma4:26b 是 CoT（Chain of Thought）推理模型，启用 reasoning 过程。50 tokens 的 max_tokens 限额不足以同时承载 reasoning 痕迹和 content 输出，导致 content 被截断为空。另外，模型默认按训练习惯在 JSON 外加 markdown 代码块包装。"
resolution_type: code_fix
---

# gemma4:26b CoT reasoning 导致 JSON 输出被截断

## Problem

gemma4:26b 通过 Ollama 本地部署，接入 LiteLLM 作为 4-Agent 系统的 LLM 底层。调试时发现：Planner 和 Writer 阶段的 JSON 输出解析失败，content 部分为空。

## Symptoms

- `json.loads(response)` 返回空字典或解析出的字段为空
- `client.generate()` 返回的 content 为空字符串
- 检查 Ollama 直接 API 响应发现 reasoning 过程输出了大量内部追踪文本，content 被挤压到 50 token 的限额之外

## What Didn't Work

- 调低 `max_tokens` 无效（已是最小值）
- 改 `temperature`、`top_p` 等生成参数无效
- 尝试不同模型（gemma4:26b 是唯一可用模型）

## Solution

**两个独立问题，分开处理：**

### 问题 A：CoT reasoning 吃 token

gemma4:26b 启用 CoT reasoning，50 tokens 不够承载 reasoning 痕迹和 content。

**解决**：LiteLLM 默认 `max_tokens=4096`，保持不变即可。4096 tokens 足够同时容纳 reasoning 和 content。

Ollama 直接 API 测试验证：

```bash
# max_tokens=50 → content 为空
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:26b","messages":[{"role":"user","content":"Say hello in one word"}],"max_tokens":50}'

# max_tokens=500 → content 正常返回 "Hello."
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:26b","messages":[{"role":"user","content":"Say hello in one word"}],"max_tokens":500}'
```

### 问题 B：JSON 被 markdown 包裹

gemma4:26b 默认在 JSON 输出外加 ` ```json ... ``` ` 包裹，破坏 `json.loads()` 解析。

**解决**：在 `planner.py`、`writer.py`、`reviewer.py` 的系统提示词中加一条硬规则：

```python
# PLANNER_SYSTEM / WRITER_SYSTEM / REVIEWER_SYSTEM
# 在写作原则或审查标准之后添加：
"""
重要规则：
- **只输出纯 JSON**，不要使用 markdown 代码块包裹，不要有 ``` 符号
"""
```

修复后 4 个 Agent 阶段输出全部干净，无 markdown 污染。

## Why This Works

gemma4:26b 的 CoT reasoning 机制会优先输出推理过程，再输出最终答案。4096 tokens 对两种内容都足够。

markdown 包裹是模型的默认行为，prompt 中显式禁止后模型会遵循——因为避免了"奖励 hacking"，直接输出 JSON 而非包裹形式。

## Prevention

- 所有接入 CoT 推理模型（gemma、Qwq、DeepSeek-R1 等）输出 JSON 的场景，统一要求 `max_tokens>=4096`
- 在系统提示词中明确禁止 markdown 代码块包裹
- 或在 `base.py` 的响应处理层做 post-processing，过滤 ` ```json` 和 ` ``` 符号
- 参考 Ollama API 响应中的 `finish_reason`：若为 `length` 说明 token 限额不足，需调大

## Related Issues

- 相关决策：[/compound learning] Prompt 外置化时机——延迟到模型行为验证稳定后再做
