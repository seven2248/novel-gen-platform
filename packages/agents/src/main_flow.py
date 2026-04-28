"""
主流程：规划 -> 写作 -> 审查 -> 回写预览
"""
import uuid
from packages.agents.src import planner, writer, reviewer, committer


def run_main_flow(
    story_state: dict,
    chapter_goal: str,
    chapter_id: str | None = None,
    chapter_num: int | None = None
) -> dict:
    """
    运行完整 4-agent 章节生成流程。

    Returns:
        {
            "plan": Planner output,
            "draft": Writer output,
            "review": Reviewer output,
            "commit_preview": Committer output,
            "correlation_id": str,
            "chapter_id": str,
            "chapter_num": int
        }
    """
    correlation_id = str(uuid.uuid4())[:8]
    chapter_id = chapter_id or f"ch-{chapter_num or 1}"
    chapter_num = chapter_num or 1

    plan = planner.run_planner(
        chapter_goal=chapter_goal,
        story_state=story_state,
        chapter_num=chapter_num
    )

    draft = writer.run_writer(
        planner_output=plan,
        story_state=story_state,
        chapter_num=chapter_num
    )

    review = reviewer.run_reviewer(
        draft_text=draft["draft_text"],
        story_state=story_state,
        planner_output=plan
    )

    commit_preview = committer.run_committer(
        draft_text=draft["draft_text"],
        reviewer_output=review,
        chapter_id=chapter_id,
        story_state=story_state,
        chapter_num=chapter_num
    )

    return {
        "plan": plan,
        "draft": draft,
        "review": review,
        "commit_preview": commit_preview,
        "correlation_id": correlation_id,
        "chapter_id": chapter_id,
        "chapter_num": chapter_num
    }
