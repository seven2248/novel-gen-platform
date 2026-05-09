---
title: "_check_hook_tracking resolution marker global-check false negative"
date: 2026-05-01
category: docs/solutions/logic-errors/
module: retrieval quality scorer
problem_type: logic_error
component: testing_framework
symptoms:
  - "_check_hook_tracking returned false positives (hooks marked as tracked) when chapter_summary contained resolution markers unrelated to those hooks"
  - "When multiple hooks exist and only one is resolved, unresolved hooks were incorrectly marked as tracked"
  - "The regression test test_one_hook_resolved_other_not_tracked initially failed after the fix was applied, exposing the bug"
root_cause: logic_error
resolution_type: code_fix
severity: medium
tags: [retrieval-quality, hook-tracking, resolution-marker, false-negative, evals]
---

# _check_hook_tracking resolution marker global-check false negative

## Problem

`_check_hook_tracking()` in `evals/scorers/retrieval_quality.py` produced false positives when a chapter summary contained resolution markers (e.g., "解开了", "揭开了") that were unrelated to specific hooks being tracked. The bug caused unresolved hooks to be incorrectly marked as tracked, breaking the hook-tracking correctness guarantee.

## Symptoms

- `_check_hook_tracking` returned `passed=True` when it should have returned `passed=False`
- Unresolved hooks were not reported in the `untracked` list
- The regression test `test_one_hook_resolved_other_not_tracked` caught the bug when it was first written (before the fix)

## What Didn't Work

**Global resolution marker check**: The original code checked `if any(marker in chapter_summary for marker in resolution_markers)` as a single boolean gate before the hook loop. If ANY resolution marker appeared ANYWHERE in the summary, ALL hooks were skipped with `continue`. This meant that when hook A was resolved and hook B was not, the global check still triggered and skipped reporting hook B as untracked.

## Solution

Replace the global resolution marker check with **per-hook resolution logic**. A hook is only marked resolved when:

1. The hook's `hook_desc` or `hook_type` appears in the chapter summary, **AND**
2. A resolution marker also appears in the summary **after** the hook mention

```python
# BEFORE (buggy):
if any(marker in chapter_summary for marker in resolution_markers):
    continue  # Skip ALL hooks if any resolution marker exists

# AFTER (fixed):
for hook in trackable_hooks:
    is_resolved = False
    if hook_desc and any(marker in chapter_summary for marker in resolution_markers):
        if hook_desc in chapter_summary:
            is_resolved = True
        elif hook_type:
            type_pos = chapter_summary.find(hook_type)
            if type_pos >= 0:
                suffix = chapter_summary[type_pos:]
                if any(marker in suffix for marker in resolution_markers):
                    is_resolved = True

    if is_resolved:
        continue  # Only skip THIS hook, not all hooks
```

The key change: resolution is scoped to each individual hook. A resolution marker in the summary only resolves a specific hook if that hook's description or type is also present. Unrelated resolution markers no longer cause false negatives for other hooks.

## Why This Works

The original bug was a **logical OR across the entire summary** instead of **per-hook AND with its own mention**. By making resolution conditional on both the hook's presence AND a resolution marker appearing after it, each hook's resolution status is computed independently. This correctly handles cases where:

- Multiple hooks exist in the same chapter
- Only some are resolved
- Resolution markers for one hook don't leak to affect others

## Prevention

- **Regression test added**: `test_one_hook_resolved_other_not_tracked` in `tests/evals/test_retrieval_quality.py` covers the "one resolved, one untracked" scenario
- **Code pattern guard**: When checking for resolution markers in loops over items, always scope the resolution check to the specific item being examined — never use a global pre-check that would skip all items
- **Test every logical branch**: Ensure each branch in conditional logic (especially `continue`/`break` statements) is exercised by at least one test case covering the "one true, one false" scenario

## Related Issues

- Commit `7aa6eb0` — `feat: W18 Phase B — retrieval quality scorer, Truth File freshness metadata`
- `evals/scorers/retrieval_quality.py` — `_check_hook_tracking()` function
- `tests/evals/test_retrieval_quality.py` — regression test `test_one_hook_resolved_other_not_tracked`