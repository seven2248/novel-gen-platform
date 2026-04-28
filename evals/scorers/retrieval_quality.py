"""
Retrieval quality scorer — evaluates whether chapter summaries retain
critical information needed for downstream chapter continuity.

Evaluates two dimensions:
1. Character status retention — summaries contain character state changes relevant to later chapters
2. Hook debt tracking — summaries track open hooks that should be resolved later

This scorer is NOT about whether retrieval works (infra), but about whether
the *content of retrieved summaries* is useful for maintaining continuity.
"""

from __future__ import annotations

from typing import Any


def score_retrieval_quality(
    chapter_summary: str,
    story_state: dict,
    target_chapter_num: int,
    checks: dict,
) -> dict:
    """
    Evaluate retrieval quality for a given chapter summary.

    Args:
        chapter_summary: The retrieved summary text for the target chapter(s)
        story_state: Full story state dict with characters, hooks, chapters
        target_chapter_num: Which chapter number is being generated
        checks: Dict of check name -> expected value.
               Supported: character_retention, hook_tracking, no_information_loss

    Returns:
        {"passed": bool, "failures": list[str], "details": dict}
    """
    failures = []
    details: dict[str, Any] = {}

    if checks.get("character_retention"):
        char_result = _check_character_retention(
            chapter_summary, story_state, target_chapter_num
        )
        details["character_retention"] = char_result
        if not char_result["passed"]:
            failures.append("character_retention")

    if checks.get("hook_tracking"):
        hook_result = _check_hook_tracking(
            chapter_summary, story_state, target_chapter_num
        )
        details["hook_tracking"] = hook_result
        if not hook_result["passed"]:
            failures.append("hook_tracking")

    if checks.get("no_information_loss"):
        loss_result = _check_information_loss(
            chapter_summary, story_state, target_chapter_num
        )
        details["no_information_loss"] = loss_result
        if not loss_result["passed"]:
            failures.append("no_information_loss")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "details": details,
    }


def _check_character_retention(
    chapter_summary: str, story_state: dict, target_chapter_num: int
) -> dict:
    """
    Check whether chapter summaries retain critical character status information.

    A 'critical' character state change is one where:
    - The character was introduced before this chapter AND
    - The character's status changed to something that affects ongoing plot AND
    - That changed status is NOT mentioned in the chapter summary
    """
    characters = story_state.get("characters", [])
    chapters = story_state.get("chapters", [])

    if not characters or target_chapter_num <= 1:
        return {"passed": True, "missing": []}

    prior_summaries: dict[int, str] = {}
    for ch in chapters:
        ch_num = ch.get("chapter_number", 0)
        if ch_num < target_chapter_num and ch.get("summary"):
            prior_summaries[ch_num] = ch["summary"]

    if not prior_summaries:
        return {"passed": True, "missing": []}

    missing = []
    status_keywords = [
        "死了",
        "去世",
        "离世",
        "受伤",
        "离开",
        "失踪",
        "陨落",
        "闭关",
        "苏醒",
        "身亡",
    ]

    for char in characters:
        char_id = char.get("id", "")
        char_name = char.get("name", "")
        if not char_name:
            continue

        introduced_chapter = char.get("chapter_introduced", 0)
        if introduced_chapter >= target_chapter_num:
            continue

        latest_status = None
        for ch_num in sorted(prior_summaries.keys(), reverse=True):
            summary_text = prior_summaries[ch_num]
            if char_name in summary_text:
                for kw in status_keywords:
                    if kw in summary_text:
                        latest_status = kw
                        break
                if latest_status:
                    break

        if latest_status:
            if latest_status not in chapter_summary and char_name in chapter_summary:
                missing.append(
                    {
                        "character": char_name,
                        "char_id": char_id,
                        "status_change": latest_status,
                        "note": f"角色在之前章节中发生了「{latest_status}」，但当前摘要未反映此状态",
                    }
                )

    for char in characters:
        introduced_ch = char.get("chapter_introduced", 0)
        if (
            0 < (target_chapter_num - introduced_ch) <= 3
            and char.get("status") == "active"
        ):
            char_name = char.get("name", "")
            if char_name:
                char_found = any(char_name in summ for summ in prior_summaries.values())
                char_in_target = char_name in chapter_summary
                if char_found and not char_in_target:
                    missing.append(
                        {
                            "character": char_name,
                            "char_id": char.get("id", ""),
                            "status_change": "active_unmentioned",
                            "note": f"角色「{char_name}」在前面章节已出现（状态活跃），但当前检索摘要中完全未提及",
                        }
                    )

    passed = len(missing) == 0
    return {"passed": passed, "missing": missing}


def _check_hook_tracking(
    chapter_summary: str, story_state: dict, target_chapter_num: int
) -> dict:
    """
    Check whether open hooks introduced before this chapter are tracked in the summary.

    A hook should appear in the summary if:
    - It was introduced at least 2 chapters before target AND
    - It is still "open" status AND
    - The chapter summary doesn't yet show it as resolved
    """
    hooks = story_state.get("hooks", [])
    chapters = story_state.get("chapters", [])

    if not hooks or target_chapter_num <= 2:
        return {"passed": True, "untracked": []}

    trackable_hooks = []
    for hook in hooks:
        introduced_ch = hook.get("chapter_introduced", 0)
        status = hook.get("status", "open")
        if (
            introduced_ch > 0
            and introduced_ch < target_chapter_num
            and status == "open"
        ):
            trackable_hooks.append(hook)

    if not trackable_hooks:
        return {"passed": True, "untracked": []}

    untracked = []
    resolution_markers = ["解开了", "揭开了", "应验", "完成了", "实现了"]

    # Per-hook resolution: only mark a hook as resolved when its
    # description/type appears in the summary AND a resolution marker
    # follows (indicating the hook's storyline was concluded).
    for hook in trackable_hooks:
        hook_id = hook.get("id", "")
        hook_type = hook.get("type", "") or ""
        hook_desc = hook.get("description", "") or ""
        introduced = hook.get("chapter_introduced", 0)

        # Check if this specific hook is resolved:
        # hook_desc appears in summary AND summary contains a resolution marker
        # near the hook_desc (the marker follows/extends the description)
        is_resolved = False
        if hook_desc and any(marker in chapter_summary for marker in resolution_markers):
            # Hook description must appear in summary
            if hook_desc in chapter_summary:
                is_resolved = True
            # Alternative: hook type appears with a resolution marker
            # e.g. summary contains "mystery揭开了" matching hook type "mystery"
            elif hook_type and hook_type in chapter_summary:
                # Check if a resolution marker appears after the type in the summary
                type_pos = chapter_summary.find(hook_type)
                if type_pos >= 0:
                    suffix = chapter_summary[type_pos:]
                    if any(marker in suffix for marker in resolution_markers):
                        is_resolved = True

        if is_resolved:
            continue

        hook_mentioned = (
            hook_id in chapter_summary
            or (hook_desc and len(hook_desc) > 2 and hook_desc in chapter_summary)
        )

        if not hook_mentioned:
            untracked.append(
                {
                    "hook_id": hook_id,
                    "hook_type": hook_type,
                    "description": hook_desc,
                    "introduced_chapter": introduced,
                    "note": f"伏笔「{hook_type}: {hook_desc[:20]}」在第{introduced}章引出后未在摘要中追踪",
                }
            )

    passed = len(untracked) == 0
    return {"passed": passed, "untracked": untracked}


def _check_information_loss(
    chapter_summary: str, story_state: dict, target_chapter_num: int
) -> dict:
    """
    Check whether key plot information from previous chapters is present in summaries.

    This is a lightweight structural check: we look for explicit plot-significant
    phrases that appeared in prior chapters and should be preserved in context.
    """
    chapters = story_state.get("chapters", [])
    plot_markers = story_state.get("plot_markers", [])

    if not chapters or target_chapter_num <= 1:
        return {"passed": True, "lost": []}

    prior_markers: list[dict] = []
    for ch in chapters:
        ch_num = ch.get("chapter_number", 0)
        if ch_num < target_chapter_num:
            prior_markers.extend(ch.get("plot_significant", []))

    all_markers = prior_markers + plot_markers

    if not all_markers:
        return {"passed": True, "lost": []}

    lost = []

    for marker in all_markers:
        marker_text = marker.get("text", "")
        marker_chapter = marker.get("chapter", 0)
        if not marker_text or marker_chapter == 0:
            continue

        if len(marker_text) < 4:
            continue

        if marker_text not in chapter_summary:
            lost.append(
                {
                    "marker": marker_text,
                    "from_chapter": marker_chapter,
                    "note": f"关键情节「{marker_text[:15]}...」在第{marker_chapter}章出现，但未在当前摘要中保留",
                }
            )

    passed = len(lost) == 0
    return {"passed": passed, "lost": lost}
