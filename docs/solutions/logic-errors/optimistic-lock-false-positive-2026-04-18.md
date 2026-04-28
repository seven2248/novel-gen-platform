---
title: Optimistic Locking False-Positive in update_chapter_state
date: 2026-04-18
category: docs/solutions/logic-errors/
module: novel-gen-api
problem_type: logic_error
component: repository
symptoms:
  - Concurrent writers targeting the same state both return True
  - Second writer's UPDATE matches 0 rows but re-fetch shows matching state → false positive
root_cause: logic_error
resolution_type: code_fix
severity: high
tags:
  - optimistic-locking
  - concurrency
  - sqlmodel
  - rowcount
  - toctou
---

# Optimistic Locking False-Positive in `update_chapter_state`

## Problem

`update_chapter_state(project_id, chapter_id, new_state, expected_version)` uses atomic `UPDATE ... WHERE version = expected_version` but verifies success by re-fetching the row and checking `version == expected_version + 1`. This fails when two concurrent writers target the **same new_state** — the second writer's `UPDATE` matches 0 rows, but the re-fetch shows the first writer's committed state (which coincidentally equals the second writer's requested state), causing a false-positive `True` return.

## Symptoms

1. Writer A and Writer B both read `version=0, state="not_started"`
2. Writer A updates to `"drafting"` — succeeds, `version` becomes 1
3. Writer B tries to update to `"drafting"` (same state) with `expected_version=0`
4. Writer B's `UPDATE WHERE version=0` matches **0 rows** (version is already 1)
5. **Bug**: Re-fetch returns `state="drafting", version=1` — matches B's requested state!
6. Old check: `if ch.version != expected_version + 1 or ch.state != new_state` → passes (false positive!)
7. Returns `(chapter, True)` — **incorrect**, B's update did NOT apply

## What Didn't Work

**Attempt 1**: Using `with self.session.connection() as conn` to read rowcount

```python
# Failed attempt
with self.session.connection() as conn:
    result = conn.execute(stmt)
    rowcount = result.rowcount
```

**Result**: `InvalidRequestError: This transaction is inactive` — the context manager conflicted with SQLModel session's transaction lifecycle.

**Attempt 2**: Removing state check from re-fetch verification

```python
# Still buggy — the core TOCTOU window remains
if ch.version != expected_version + 1:
    return ch, False
return ch, True  # Still passes on coincidental state match!
```

**Result**: Still fails because coincidental state match triggers false positive.

## Solution

Use `session.exec(stmt).rowcount` as the authoritative success signal:

```python
def update_chapter_state(self, project_id: str, chapter_id: str, new_state: str, expected_version: int | None = None) -> tuple[ChapterState, bool]:
    if expected_version is not None:
        # Atomic UPDATE ... WHERE version = expected_version
        # Execute via session.exec() to get rowcount: 1 = my UPDATE hit,
        # 0 = another writer already changed the version (my UPDATE is lost).
        # The subsequent re-fetch is only for the return value, not for
        # confirmation — rowcount is the authoritative signal.
        stmt = (
            update(ChapterState)
            .where(
                ChapterState.project_id == project_id,
                ChapterState.chapter_id == chapter_id,
                ChapterState.version == expected_version,
            )
            .values(
                state=new_state,
                version=ChapterState.version + 1,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        try:
            result = self.session.exec(stmt)
            rowcount = result.rowcount  # AUTHORITATIVE SIGNAL
            self.session.commit()
        except Exception:
            return None, False

        if rowcount == 0:
            ch = self.get_chapter(project_id, chapter_id)
            return ch, False
        ch = self.get_chapter(project_id, chapter_id)
        return ch, True
```

**Logic**:
- `rowcount == 1`: My `UPDATE` hit → return `(chapter, True)`
- `rowcount == 0`: Version changed by another writer → re-fetch only for return value, return `(chapter, False)`

**Modified file**: `services/api/app/repositories/story_state_repository.py`

## Why This Works

1. **rowcount is the authoritative signal**: SQLAlchemy's `rowcount` reflects the actual number of rows matched by the `UPDATE` statement, not the state of the database after other writers commit.
2. **No TOCTOU window**: The check happens immediately after `session.exec(stmt)`, before `commit()` — there's no window for another transaction to interleave.
3. **Re-fetch is only for return value**: We re-fetch to return the current chapter state to the caller, but the **decision** is based purely on `rowcount`.

## Prevention

### Test Coverage

New test explicitly asserts this bug scenario:

```python
def test_concurrent_writes_same_target_state_both_return_false(self, temp_db):
    """
    Both A and B read version=0 simultaneously and both try to set the SAME state.
    The first writer commits; the second's UPDATE must hit 0 rows (rowcount=0)
    and correctly return False — even though the re-fetched state matches the
    target state that both writers requested.
    """
    engine, _ = temp_db
    # ... setup ...

    # A writes first with expected_version=0
    updated_a, ok_a = repo_a.update_chapter_state(
        "proj-1", "ch-1", "drafting", expected_version=ver_a
    )
    assert ok_a is True

    # B tries to write the SAME state "drafting" with expected_version=0
    updated_b, ok_b = repo_b.update_chapter_state(
        "proj-1", "ch-1", "drafting", expected_version=ver_b
    )
    # Must be False — B's UPDATE did not apply
    assert ok_b is False
    # The re-fetched state will be A's write (state="drafting"), which
    # coincidentally matches B's requested state — that MUST NOT fool us
    assert updated_b.state == "drafting"
```

### Code Review Checklist

When implementing optimistic locking:
- [ ] Always use `rowcount` (not re-fetch verification) as the success signal
- [ ] Verify the test covers **same-target-state** concurrency
- [ ] Avoid session context managers that conflict with transaction lifecycle

---

# Related Issue: Database Error Detail Leak

## Problem

In `services/api/app/routers/events.py`, the HTTPException detail contained internal error information:

```python
# Before (line 46)
raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
```

This leaks internal exception details to API consumers — potential security risk.

## Solution

```python
# After (line 46)
raise HTTPException(status_code=500, detail="Database error") from exc
```

**Modified file**: `services/api/app/routers/events.py`

## Why This Works

Generic error messages prevent internal exception details from leaking to API consumers. The original exception is still chained (`from exc`) for server-side logging, but the response body contains no sensitive information.

## Prevention

- [ ] All HTTPException messages in routers should use generic strings, never f-strings with `{exc}` or other internal details
- [ ] Code reviewer should flag any `detail=f"...{exc}"` patterns