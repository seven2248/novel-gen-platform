import json
from packages.agents.src.schema_validator import validate_payload


def run_committer(
    draft_text: str,
    reviewer_output: dict,
    chapter_id: str,
    story_state: dict,
    chapter_num: int | None = None,
    correlation_id: str = "",
) -> dict:
    """Committer 生成状态 diff 预览（不直接写入）"""

    if chapter_num is None:
        old_chapters = story_state.get("chapters", [])
        chapter_num = len(old_chapters) + 1

    state_diff = {
        "add": [
            {
                "type": "chapter_summary",
                "chapter_id": chapter_id,
                "chapter_number": chapter_num,
                "summary": draft_text[:200] + "...",
                "word_count": len(draft_text),
                "state": "committed",
            }
        ],
        "update": [],
        "remove": [],
    }

    result = {
        "state_diff": state_diff,
        "projection_refresh_targets": ["chapters", "hooks"],
        "warnings": [],
    }

    if reviewer_output.get("risk_level") == "high":
        result["warnings"].append(
            {
                "type": "high_risk",
                "message": "审查评分偏低，建议人工确认后再回写",
                "severity": "warn",
            }
        )

    valid, err = validate_payload(result, "agent_io/committer_output.schema.json")
    if not valid:
        raise ValueError(f"Committer output validation failed: {err}")

    return result
