---
title: FastAPI Router Exception Handling — except Exception Intercepts Pydantic Validation
date: 2026-04-16
category: docs/solutions/logic-errors/
module: novel-gen-api
problem_type: logic_error
component: service_object
symptoms:
  - Oversized payload (>10MB) returns HTTP 500 instead of HTTP 422
  - Unused variable `loop = asyncio.get_running_loop()` assigned but never used in two router files
root_cause: logic_error
resolution_type: code_fix
severity: medium
tags:
  - fastapi
  - exception-handling
  - pydantic-validation
  - unused-variable
  - http-422
  - asyncio
---

# FastAPI Router Exception Handling — `except Exception` Intercepts Pydantic Validation

## Problem

两个 FastAPI 路由中存在逻辑错误，导致 API 在特定场景下返回错误的 HTTP 状态码，同时存在未使用的死代码。

## Symptoms

- **Bug 1**: 发送超大 `story_state`（>10MB）时，API 返回 `HTTP 500` 而非 `HTTP 422 Unprocessable Entity`
- **Bug 2**: `agent_runs.py` 和 `local_rewrites.py` 中存在赋值后从未使用的变量 `loop = asyncio.get_running_loop()`

## What Didn't Work

**错误的修复尝试**：在两个路由中添加了 `except Exception → HTTP 500` 处理器来处理未知异常，但没有考虑到 FastAPI 的 Pydantic 验证层也会抛出 `Exception` 子类。

Python 行为验证确认：
```python
# 验证代码
try:
    1/0
except Exception as e:
    print(type(e).__name__)  # ZeroDivisionError (继承自Exception)
```
结论：`except Exception` 会捕获所有继承自 `Exception` 的异常，包括 Pydantic 的 `RequestValidationError`。

## Solution

### Bug 1 — `except Exception` 拦截 Pydantic 校验异常

**问题本质**：`field_validator` 抛出 `ValueError` → FastAPI 包装为 `RequestValidationError`（继承链：`RequestValidationError → ValueError → Exception`）→ `except Exception` 捕获 → 返回 HTTP 500。

**修复**：在 `except Exception` 之前添加 `except ValueError: raise`，让 FastAPI 原生处理器返回 HTTP 422。

**修改文件**：`services/api/app/routers/agent_runs.py`、`services/api/app/routers/local_rewrites.py`

```python
# 修改前
try:
    return await asyncio.wait_for(afuture, timeout=float(LLM_TIMEOUT_SECONDS))
except asyncio.TimeoutError:
    afuture.cancel()
    raise HTTPException(status_code=504, ...)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Agent run failed: {e!s}")

# 修改后
try:
    return await asyncio.wait_for(afuture, timeout=float(LLM_TIMEOUT_SECONDS))
except asyncio.TimeoutError:
    afuture.cancel()
    raise HTTPException(status_code=504, ...)
except ValueError:
    raise  # re-raise so FastAPI returns 422
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Agent run failed: {e!s}")
```

### Bug 2 — 删除未使用的 `loop` 变量

**问题本质**：`asyncio.wrap_future()` 不需要显式获取事件循环。`loop = asyncio.get_running_loop()` 赋值后从未引用。

**修复**：删除这两行赋值语句。

```python
# 修改前
loop = asyncio.get_running_loop()
future = _llm_pool.submit(run_main_flow, ...)

# 修改后
future = _llm_pool.submit(run_main_flow, ...)
```

## Why This Works

1. **`except ValueError: raise` 的原理**：`ValueError` 在 `Exception` 之前被捕获并重新抛出，FastAPI 的异常处理中间件继续处理，返回正确的 HTTP 422 状态码。
2. **`loop` 变量删除的原理**：`asyncio.wrap_future()` 从当前事件循环隐式获取上下文，无需显式传递。删除死代码避免未来开发者的困惑。

## Prevention

1. **在 FastAPI async 端点中添加 generic `except Exception` 时**：
   - 始终在 `except Exception` 前添加 `except ValueError: raise`，让 FastAPI 原生处理 Pydantic 校验异常
   - 为任何已知应由框架处理的异常类型添加明确的 `except` 分支

2. **错误路径测试**：在测试中对 oversized payload 验证返回 HTTP 422 而非 500：
   ```python
   def test_oversized_story_state_returns_422(client):
       large_state = {"data": "x" * (11 * 1024 * 1024)}  # >10MB
       response = client.post("/agent-runs/main-flow", json={
           "story_state": large_state, "chapter_goal": "test"
       })
       assert response.status_code == 422  # NOT 500
   ```

3. **Code Review Checklist**：reviewer 检查所有新增 generic exception handler 时，确认 Pydantic 校验异常（`ValueError`/`RequestValidationError`）是否需要显式重新抛出

## Related Issues

- 相关审查发现：`docs/solutions/logic-errors/multi-fix-code-review-p1-p2-logic-errors-2026-04-15.md`（同类问题的历史修复记录）
