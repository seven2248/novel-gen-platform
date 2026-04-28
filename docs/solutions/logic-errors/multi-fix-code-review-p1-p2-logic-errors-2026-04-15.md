---
title: "代码审查修复：P1/P2 逻辑错误批量修复"
date: "2026-04-15"
category: "docs/solutions/logic-errors/"
module: "agents"
problem_type: "logic_error"
component: "development_workflow"
severity: "high"
tags:
  - code-review
  - P1
  - P2
  - bug-fix
  - logic-error
  - 2026-04-15
symptoms:
  - KeyError运行时异常
  - 废弃API警告
  - 测试污染
  - 异常吞没
root_cause: "logic_error"
resolution_type: "code_fix"
---

# 代码审查修复：P1/P2 逻辑错误批量修复

## 背景

2026-04-15 下午，通过 `/ce:work` 处理同事的代码审查意见（`docs/2026-04-15_W16代码审查问题清单.md`），修复了 7 个问题。修复后执行 `/ce:review` 复核，发现并修缮了第 8 个遗漏问题。

---

## Bug 1: P1-2 — `committer.py` chapter_num 硬编码

### Problem
`chapter_num = len(old_chapters) + 1` 在 `run_committer` 中硬编码。连续多章生成时若 `story_state` 未实时更新，每次调用都从相同的旧章节列表长度重新计算，导致每章的 `chapter_num` 都是 1。

### Symptoms
章节号不正确，连续生成多章时均显示「第 1 章」。

### What Didn't Work
- 尝试在 committer 内部维护状态 → committer 被设计为无状态工具
- 尝试在调用前手动更新 `story_state.chapters` → 调用方分散，难以统一管控

### Solution

`run_committer` 新增可选参数，默认保留原有计算逻辑作为向后兼容：

```python
# committer.py
def run_committer(
    draft_text: str,
    reviewer_output: dict,
    chapter_id: str,
    story_state: dict,
    chapter_num: int | None = None  # 新增
) -> dict:
    if chapter_num is None:
        old_chapters = story_state.get("chapters", [])
        chapter_num = len(old_chapters) + 1
    # ... 后续逻辑不变
```

调用方同步传入：

```python
# workflow.py
commit_preview = _call_committer(
    draft_result, review_result, chapter_id, story_state, chapter_num
)

# main_flow.py
commit_preview = committer.run_committer(
    draft_text=draft["draft_text"],
    reviewer_output=review,
    chapter_id=chapter_id,
    story_state=story_state,
    chapter_num=chapter_num  # 显式传递
)
```

### Why This Works
参数化使计算职责明确化：workflow 层知道当前是第几章，committer 纯执行。`None` 默认值保持向后兼容。

### Prevention
- 避免在工具函数内计算与「调用上下文」相关的状态量
- 参数显式传递，比隐式查找更可靠

---

## Bug 2: P1-3 — `truth_exporter.py` 废弃 API + 缺失导入

### Problem
(1) 使用已废弃的 `repo.session.query(Model).filter(...)` SQLAlchemy 1.x API；(2) 修复时只改了查询风格但未导入 `select`，导致运行时 `NameError: name 'select' is not defined`。

### Symptoms
```
NameError: name 'select' is not defined
```

### What Didn't Work
- 改用 `exec(select(...))` 风格后，未检查 `select` 的命名空间

### Solution

```python
# truth_exporter.py 顶部添加导入
from sqlmodel import select

# 替换废弃调用
# 旧: repo.session.query(ChapterState).filter(ChapterState.project_id == project_id).all()
# 新:
chapters = repo.session.exec(
    select(ChapterState).where(ChapterState.project_id == project_id)
).all()
```

### Why This Works
SQLModel 基于 SQLAlchemy 2.0，`session.exec(select(...))` 是 2.0 的标准查询接口。显式导入 `select` 确保命名空间正确。

### Prevention
- 使用新版本框架时，同步更新 API 调用方式
- 改 API 时同步检查相关导入是否完整

---

## Bug 3: P1-4 — 中文函数名 `export_chapter增量`

### Problem
函数名含中文字符。IDE 自动补全异常、logging 输出乱码、traceback 可读性差，多工具链（lint/format/import analysis）兼容性问题。

### Symptoms
中文标识符在 traceback 中显示异常，grep 检索困难。

### Solution

```python
# truth_exporter.py
def export_chapter_delta(repo, project_id: str, chapter_id: str,
                         output_dir: str | Path | None = None) -> dict[str, Path]:
    ...

# workflow.py — 调用处同步更新
from packages.agents.src.truth_exporter import export_chapter_delta
export_chapter_delta(repo, project_id, chapter_id, truth_output_dir)
```

### Why This Works
纯 ASCII 标识符在所有工具链（Python、IDE、shell、git、CI）中行为一致。

### Prevention
- 团队约定：代码、函数名、变量名只用 ASCII
- 中文可用于注释和文档，不用于标识符

---

## Bug 4: P1-1 — `_print_result` 直接嵌套键访问导致 KeyError

### Problem
`result['draft']['draft_text']` 直接嵌套键访问，若 `draft_text` 缺失（但 `draft` 存在）则抛出 `KeyError`。

### Symptoms
```
KeyError: 'draft_text'
```

### Solution

```python
def _print_result(result: dict) -> None:
    try:
        draft_text = result.get("draft", {}).get("draft_text", "[无草稿]")
        review_score = result.get("review", {}).get("readability_score", "N/A")
        # ... 其他字段
    except (KeyError, TypeError) as e:
        print(f"\n[警告] 结果打印失败: {e}")
        print("[原始结果]")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
```

### Why This Works
- 链式 `.get()` + `or {}` 处理中间键缺失
- 完整 `try/except` 兜底，打印原始数据便于调试

### Prevention
- 永远不要直接嵌套键访问外部输入数据
- JSON/dict 解析必须用 `.get()` 或 try/except 保护

---

## Bug 5: P1-5 + 复核 P1 — `schema_validator.py` 和 `workflow.py` 的 `except Exception` 静默吞异常

### Problem（两处）
(1) `schema_validator.py` 在 `except (json.JSONDecodeError, OSError)` 之后还有 `except Exception` 兜底，所有编程错误被静默捕获；(2) `workflow.py:78` 阶段 7 Truth Files 导出处同样使用 `except Exception`。

> **注意**：这是两次修复才完成的问题。第一次修复只改了异常顺序或改为 `pass`，但兜底的 `except Exception` 仍然存在。

### Symptoms
编程错误（TypeError、AttributeError）被静默吞掉，validator 返回 `False` 而非抛出异常。

### Solution

```python
# schema_validator.py — 移除末尾的 except Exception
try:
    schema = load_schema(schema_name)
    validate(instance=payload, schema=schema)
    return True, ""
except (json.JSONDecodeError, OSError) as e:
    return False, str(e)
# 不再有 except Exception 兜底 — 编程错误正常上抛

# workflow.py — 同样替换
try:
    export_chapter_delta(repo, project_id, chapter_id, truth_output_dir)
except (json.JSONDecodeError, OSError) as exc:
    truth_export_warning = str(exc)
```

### Why This Works
框架 / 工具函数的「预期异常」（文件不存在、JSON 格式错误）应被捕获并转为 `False` 或 warning；编程错误不属于预期范围，应正常上抛让调用方发现。

### Prevention
- 永远不要用 `except Exception` 兜底，除非是顶层 entry point
- 工具函数应区分「预期业务异常」和「编程错误」，只吞前者
- 搜索全 codebase `except Exception` 并逐个评估是否合理

---

## Bug 6: P2-5 — 全局 `autouse=True` mock 干扰集成测试

### Problem
`tests/conftest.py` 的 `autouse=True` fixture 对所有测试自动 mock，导致 `tests/agents/` 外的集成测试（需要真实 LLM 调用）被静默 mock，false positive。

### Symptoms
集成测试通过但实际功能从未真正调用 LLM。

### Solution

```python
# tests/conftest.py（根级）— 移除 autouse mock
# 仅保留 temp_db, session, fake_project, fake_story_state 等基础设施 fixture

# tests/agents/conftest.py（新建）— mock 下沉到此处
@pytest.fixture(autouse=True)
def mock_agents():
    from packages.agents.src.base import set_mock_responses, reset_mock, MOCK_RESPONSES
    set_mock_responses(MOCK_RESPONSES)
    yield
    reset_mock()
```

### Why This Works
`autouse` 范围收缩到最小必要（只影响 agents 目录下的单元测试）；集成测试不自动 mock，可以按需选择是否使用真实 LLM。

### Prevention
- `autouse=True` 仅在明确知道「所有测试都需要」时使用
- 集成测试目录应独立 conftest，不继承根级 autouse fixture

---

## Bug 7: P2-1 — `BaseAgent` 行为差异未标注

### Problem
`BaseAgent.run()` 的执行顺序（fallback → validate）与现有 agent（validate → fallback）相反，且 `get_fallback()` 默认返回 `{}`，若子类未重写则 fallback 形同虚设。迁移时会产生预期外的行为差异。

### Solution

在 `BaseAgent` 类文档字符串中显式注明：

```python
class BaseAgent(ABC):
    """
    Agent 抽象基类，定义 run 流程。

    注意（与现有 agent 的行为差异）：
    - JSON 解析失败时 → get_fallback() → schema 验证
      现有 agent（planner/writer/reviewer）的 run_* 函数则是：
      JSON 解析失败时 fallback → schema 验证失败时 raise ValueError
      两种行为顺序不一致，迁移时需对齐。
    - get_fallback() 默认返回 {}，若子类未重写且 JSON 解析失败，
      空 dict 会触发 schema 验证异常，fallback 相当于形同虚设。
      子类必须重写 get_fallback() 以提供有意义的兜底值。
    """
```

### Why This Works
文档显式说明差异，迁移者能提前知晓，而非在 bug 出现后再排查。

### Prevention
- 类行为与已有实现不一致时，必须在 docstring 显式注明
- 建立行为差异检查清单，跨 agent 迁移前必读

---

## 总结

本次批量修复涵盖 8 个问题，涉及 committer、truth_exporter、schema_validator、cli、workflow、base_agent、tests 等模块。

| Bug | 严重级 | 根因 | 类型 |
|-----|--------|------|------|
| chapter_num 硬编码 | P1 | logic_error | 代码修复 |
| truth_exporter 废弃 API | P1 | wrong_api + missing_import | 代码修复 |
| 中文函数名 | P1 | naming_convention | 代码修复 |
| _print_result KeyError | P1 | missing_validation | 代码修复 |
| schema_validator except Exception | P1 | logic_error | 代码修复 |
| workflow.py except Exception | P1 | logic_error | 代码修复（复核发现）|
| autouse mock 干扰集成测试 | P2 | test_isolation | 代码修复 |
| BaseAgent 行为差异未标注 | P2 | inadequate_documentation | 文档修复 |

**核心原则**：
1. 工具函数不吞编程错误，只处理预期业务异常
2. 参数显式传递，不在工具内部隐式计算上下文相关状态
3. 所有导入在移动代码时同步检查
4. autouse 只在必要时使用，集成测试和单元测试隔离

---

## Related Issues
- `docs/2026-04-15_W16代码审查问题清单.md` — 审查意见原文
- `docs/2026-04-15_W16小说生成系统开发记录.md` — 开发日志
- `docs/solutions/logic-errors/fastapi-router-exception-handling-2026-04-16.md` — FastAPI 路由层 `except Exception` 拦截 Pydantic 校验异常（同类逻辑错误）
