"""
主流程：规划 -> 写作 -> 审查 -> 回写预览

内部委托给 orchestrator.run_orchestrator()。
保留原有签名以兼容 agent_runs.py。
"""

from packages.agents.src.orchestrator import run_orchestrator


def run_main_flow(
    story_state: dict,
    chapter_goal: str,
    chapter_id: str | None = None,
    chapter_num: int | None = None,
) -> dict:
    """
    运行完整 4-agent 章节生成流程。

    Returns:
        {
            "plan": Planner output,
            "draft": Writer output,
            "review": Reviewer output,
            "commit_preview": Committer output,
            "warnings": list,        # W19 新增：聚合的 warning 列表
            "correlation_id": str,
            "chapter_id": str,
            "chapter_num": int
        }
    """
    result = run_orchestrator(
        story_state=story_state,
        chapter_goal=chapter_goal,
        chapter_id=chapter_id,
        chapter_num=chapter_num,
    )
    # 保持向后兼容：旧调用方期望的字段
    return {
        "plan": result["plan"],
        "draft": result["draft"],
        "review": result["review"],
        "commit_preview": result["commit_preview"],
        "correlation_id": result["correlation_id"],
        "chapter_id": result["chapter_id"],
        "chapter_num": result["chapter_num"],
        # 新增字段（向后兼容调用方忽略即可）
        "warnings": result["warnings"],
        "state_transition": result["state_transition"],
    }
