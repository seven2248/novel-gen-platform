"""
Orchestrator — 轻量级 Agent 编排层

职责：
1. 生成 correlation_id 并透传给每一步
2. 收集各 Agent 的 warning，统一返回
3. 状态机迁移合法性检查（在 API 层通过 repo 调用，这里只做编排）

不做什么（来自路线图约束）：
- 不做 workflow DSL
- 不做可配置的 agent 链路编排
- 不做失败重试策略
"""

import uuid
from packages.agents.src import planner, writer, reviewer, committer


# ---------------------------------------------------------------------------
# 状态机合法性
# ---------------------------------------------------------------------------

# ChapterState 合法值：not_started, drafting, reviewing, committed
VALID_STATES = {"not_started", "drafting", "reviewing", "committed"}

# 正常前进方向：允许跳过中间状态（如 not_started → reviewing）
FORWARD_TRANSITIONS = {
    "not_started": {"drafting", "reviewing"},
    "drafting": {"reviewing"},
    "reviewing": {"committed", "drafting"},  # 可以退回去重写
    "committed": {"reviewing"},  # committed → reviewing 审稿重修
}

# 需要 explicit_reset 的反向跳转（只有显式调用 reset 才能触发）
RESET_REQUIRED_TRANSITIONS = {
    "committed": {"drafting"},  # 必须显式 reset 才能从 committed 回到 drafting
}


def validate_state_transition(
    current_state: str, new_state: str, explicit_reset: bool = False
) -> tuple[bool, str]:
    """
    检查章节状态迁移是否合法。

    Returns:
        (is_valid, reason): 是否合法，及原因说明

    规则：
    - committed → drafting 必须 explicit_reset=True
    - 其它 forward 方向自由迁移
    - 未知状态拒绝
    """
    if new_state not in VALID_STATES:
        return False, f"未知状态: {new_state}"

    if current_state not in VALID_STATES:
        # 新建章节，任意合法状态都可接受
        return True, ""

    # 需要 reset 的反向跳转
    if (
        current_state in RESET_REQUIRED_TRANSITIONS
        and new_state in RESET_REQUIRED_TRANSITIONS[current_state]
    ):
        if not explicit_reset:
            return False, (
                f"状态迁移 {current_state}→{new_state} 需要 explicit_reset=True。"
                "章节已 committed，必须显式重置才能回到 drafting。"
            )
        return True, "explicit_reset"

    # forward 方向自由迁移
    if new_state in FORWARD_TRANSITIONS.get(current_state, set()):
        return True, "forward"

    # 其它全部拒绝（比如 committed → not_started）
    return False, f"非法状态迁移: {current_state} → {new_state}"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_orchestrator(
    story_state: dict,
    chapter_goal: str,
    chapter_id: str | None = None,
    chapter_num: int | None = None,
    correlation_id: str | None = None,
) -> dict:
    """
    轻量级编排器，运行完整 4-agent 章节生成流程。

    Params:
        story_state:    故事状态字典
        chapter_goal:   本章目标描述
        chapter_id:     章节 ID（可选，默认自动生成）
        chapter_num:    章节序号（可选）
        correlation_id: 链路追踪 ID（可选，默认自动生成）

    Returns:
        {
            "plan":            Planner 输出（包含 correlation_id）,
            "draft":           Writer 输出（包含 correlation_id）,
            "review":          Reviewer 输出（包含 correlation_id）,
            "commit_preview":  Committer 输出（包含 correlation_id）,
            "warnings":        聚合的 warning 列表,
            "correlation_id":  链路追踪 ID,
            "chapter_id":      实际使用的章节 ID,
            "chapter_num":     章节序号,
            "state_transition": None,   # 由 API 层填充
        }
    """
    # correlation_id：orchestrator 生成，往下透传
    correlation_id = correlation_id or str(uuid.uuid4())[:8]
    chapter_id = chapter_id or f"ch-{chapter_num or 1}"
    chapter_num = chapter_num or 1

    # -------- Planner --------
    plan = planner.run_planner(
        chapter_goal=chapter_goal,
        story_state=story_state,
        chapter_num=chapter_num,
        correlation_id=correlation_id,
    )

    # -------- Writer --------
    draft = writer.run_writer(
        planner_output=plan,
        story_state=story_state,
        chapter_num=chapter_num,
        correlation_id=correlation_id,
    )

    # -------- Reviewer --------
    review = reviewer.run_reviewer(
        draft_text=draft["draft_text"],
        story_state=story_state,
        planner_output=plan,
        correlation_id=correlation_id,
    )

    # -------- Committer --------
    commit_preview = committer.run_committer(
        draft_text=draft["draft_text"],
        reviewer_output=review,
        chapter_id=chapter_id,
        story_state=story_state,
        chapter_num=chapter_num,
        correlation_id=correlation_id,
    )

    # -------- Warning 聚合 --------
    # 从各 agent 输出中提取 warnings，统一平铺返回
    # 使用 dict spread 避免原地修改 agent 返回值
    all_warnings = []

    for w in plan.get("warnings", []):
        all_warnings.append({"_source": "planner", **w})

    for w in draft.get("warnings", []):
        all_warnings.append({"_source": "writer", **w})

    # Reviewer：consistency_issues + style_issues 转为 warnings
    for issue in review.get("consistency_issues", []):
        all_warnings.append(
            {
                "_source": "reviewer",
                "type": issue.get("type", "consistency"),
                "severity": issue.get("severity", "major"),
                "message": issue.get("description", ""),
                "location": issue.get("location", ""),
            }
        )

    for issue in review.get("style_issues", []):
        all_warnings.append(
            {
                "_source": "reviewer",
                "type": issue.get("type", "style"),
                "severity": issue.get("severity", "minor"),
                "message": issue.get("description", ""),
                "location": issue.get("location", ""),
            }
        )

    # Reviewer risk_level 也作为 warning
    if review.get("risk_level") == "high":
        all_warnings.append(
            {
                "_source": "reviewer",
                "type": "risk",
                "severity": "critical",
                "message": "审查 risk_level 为 high，建议人工确认后再回写",
            }
        )

    # Committer warnings（已经是标准格式）
    for w in commit_preview.get("warnings", []):
        all_warnings.append({"_source": "committer", **w})

    return {
        "plan": plan,
        "draft": draft,
        "review": review,
        "commit_preview": commit_preview,
        "warnings": all_warnings,
        "correlation_id": correlation_id,
        "chapter_id": chapter_id,
        "chapter_num": chapter_num,
        "state_transition": None,  # 由 API 层填充
    }
