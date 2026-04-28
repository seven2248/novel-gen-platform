"""
Story constraint scorer — narrow checks for Phase A minimum regression.
"""
import re


def score_story_constraints(draft_text: str, checks: dict) -> dict:
    """
    Evaluate draft against simple constraint checks.

    Args:
        draft_text: The generated chapter or rewrite text
        checks: Dict of check name -> expected value.
               Supported: min_word_count, hook_presence, no_forbidden_patterns,
                          forbidden_patterns (list), diff_non_empty, tone_shift_detected

    Returns:
        {"passed": bool, "failures": list[str]}
    """
    failures = []

    min_words = checks.get("min_word_count", 0)
    # Count words: ASCII alphanumerics as words, CJK characters individually.
    # Chinese punctuation (，。！？：；""''【】（） etc.) is NOT counted.
    # This uses the U+4E00–U+9FFF CJK Unified Ideographs block which covers
    # most Chinese/Japanese/Korean Han characters but excludes CJK punctuation.
    word_count = len(re.findall(r'[A-Za-z0-9_]+|[一-龥]', draft_text))
    if word_count < min_words:
        failures.append("min_word_count")

    if checks.get("hook_presence"):
        has_hook = "？" in draft_text or "！" in draft_text or "……" in draft_text
        if not has_hook:
            failures.append("hook_presence")

    if checks.get("no_forbidden_patterns"):
        forbidden = checks.get("forbidden_patterns", [])
        for pattern in forbidden:
            if pattern in draft_text:
                failures.append(f"forbidden_pattern:{pattern}")
                break

    return {"passed": len(failures) == 0, "failures": failures}


def score_local_rewrite(result: dict, checks: dict) -> dict:
    """
    Evaluate local rewrite result against constraint checks.

    Args:
        result: run_local_rewrite() output dict
        checks: Dict of check name -> expected value.
               Supported: diff_non_empty, tone_shift_detected

    Returns:
        {"passed": bool, "failures": list[str]}
    """
    failures = []

    if checks.get("diff_non_empty"):
        diff_lines = result.get("diff_lines", [])
        # Filter out blank lines and the header lines (---, +++, @@)
        meaningful = [l for l in diff_lines if l and not l.startswith(("---", "+++", "@@", "index"))]
        if not meaningful:
            failures.append("diff_non_empty")

    if checks.get("tone_shift_detected"):
        tone_shift = result.get("tone_shift", "")
        if not tone_shift or tone_shift == "无变化":
            failures.append("tone_shift_detected")

    return {"passed": len(failures) == 0, "failures": failures}
