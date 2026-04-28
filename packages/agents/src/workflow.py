"""
章节生成编排层：调用 main_flow + repository 完成真实落库和事件日志
"""
import copy
import json
import uuid
from pathlib import Path


def run_chapter_flow_with_db(
    repo,
    project_id: str,
    chapter_goal: str,
    story_state: dict,
    chapter_num: int | None = None,
    chapter_id: str | None = None,
    truth_output_dir: str | Path | None = None,
) -> dict:
    """
    运行章节生成流程并将结果回写到 Story State Core。

    Args:
        repo: StoryStateRepository 实例
        project_id: 项目 ID
        chapter_goal: 章节目标描述
        story_state: 当前故事状态字典
        chapter_num: 章节序号
        chapter_id: 章节 ID（可选）
        truth_output_dir: Truth Files 输出目录（None 则用默认路径）

    Returns:
        main_flow 的完整输出（包含 plan/draft/review/commit_preview）
    """
    correlation_id = str(uuid.uuid4())[:8]
    chapter_id = chapter_id or f"ch-{chapter_num or 1}"
    chapter_num = chapter_num or 1

    # Retrieve recent chapter summaries from DB and inject into story_state
    # so the writer has contextual continuity without relying on in-memory accumulation alone
    if chapter_num > 1:
        recent = repo.get_recent_chapters(project_id, limit=5)
        if recent:
            story_state = copy.deepcopy(story_state)
            existing_ids = {c["chapter_id"] for c in story_state.get("chapters", [])}
            for ch in reversed(recent):  # oldest-first for the dict merge
                if ch["chapter_id"] not in existing_ids:
                    story_state.setdefault("chapters", []).append(ch)
                    existing_ids.add(ch["chapter_id"])

    # 阶段 1: Planner
    plan_result = _log_and_run(
        repo, project_id, "planner.completed", correlation_id, "",
        lambda: _call_planner(chapter_goal, story_state, chapter_num)
    )

    # 阶段 2: Writer
    draft_result = _log_and_run(
        repo, project_id, "writer.completed", correlation_id, correlation_id,
        lambda: _call_writer(plan_result, story_state, chapter_num)
    )

    # 阶段 3: Reviewer
    review_result = _log_and_run(
        repo, project_id, "reviewer.completed", correlation_id, correlation_id,
        lambda: _call_reviewer(draft_result, story_state, plan_result)
    )

    # 阶段 4: Committer（生成 state_diff，不做回写）
    commit_preview = _call_committer(draft_result, review_result, chapter_id, story_state, chapter_num)

    # 阶段 5: Committer preview 完成
    repo.append_event(
        project_id=project_id,
        event_type="committer.previewed",
        actor_type="agent",
        correlation_id=correlation_id,
        causation_id=correlation_id,
        payload={"chapter_id": chapter_id, "chapter_num": chapter_num}
    )

    # 阶段 6: 执行 state_diff（真实落库）
    _apply_state_diff(repo, project_id, chapter_id, chapter_num, commit_preview, draft_result, correlation_id)

    # 阶段 7: 增量刷新 Truth Files 投影
    truth_export_warning = None
    try:
        from packages.agents.src.truth_exporter import export_chapter_delta
        export_chapter_delta(repo, project_id, chapter_id, truth_output_dir)
    except (json.JSONDecodeError, OSError) as exc:
        truth_export_warning = str(exc)

    return {
        "plan": plan_result,
        "draft": draft_result,
        "review": review_result,
        "commit_preview": commit_preview,
        "correlation_id": correlation_id,
        "chapter_id": chapter_id,
        "chapter_num": chapter_num,
        "truth_export_warning": truth_export_warning,
    }


def generate_chapters(
    repo,
    project_id: str,
    chapter_goals: list[str],
    story_state: dict,
    start_num: int = 1,
    truth_output_dir: str | Path | None = None,
) -> list[dict]:
    """
    连续生成多个章节，每章都走完整闭环并累计状态。

    Args:
        repo: StoryStateRepository 实例
        project_id: 项目 ID
        chapter_goals: 每章的目标描述列表
        story_state: 初始故事状态（会被实时更新）
        start_num: 起始章节号

    Returns:
        每章的运行结果列表
    """
    results = []
    current_story_state = copy.deepcopy(story_state)  # 深拷贝，防止修改调用方状态

    for i, goal in enumerate(chapter_goals):
        chapter_num = start_num + i
        chapter_id = f"ch-{chapter_num}"

        result = run_chapter_flow_with_db(
            repo=repo,
            project_id=project_id,
            chapter_goal=goal,
            story_state=current_story_state,
            chapter_num=chapter_num,
            chapter_id=chapter_id,
            truth_output_dir=truth_output_dir,
        )
        results.append(result)

        # 把本章的摘要写回 story_state，供下一章使用
        _advance_story_state(current_story_state, result)

    return results


# ------------------------------------------------------------------
# 内部辅助
# ------------------------------------------------------------------

def _log_and_run(repo, project_id, event_type, correlation_id, causation_id, fn):
    """执行函数并记录事件日志。"""
    result = fn()
    repo.append_event(
        project_id=project_id,
        event_type=event_type,
        actor_type="agent",
        correlation_id=correlation_id,
        causation_id=causation_id,
        payload=None
    )
    return result


def _call_planner(chapter_goal, story_state, chapter_num):
    from packages.agents.src import planner
    return planner.run_planner(chapter_goal, story_state, chapter_num)


def _call_writer(planner_output, story_state, chapter_num):
    from packages.agents.src import writer
    return writer.run_writer(planner_output, story_state, chapter_num)


def _call_reviewer(draft_result, story_state, planner_output):
    from packages.agents.src import reviewer
    return reviewer.run_reviewer(draft_result["draft_text"], story_state, planner_output)


def _call_committer(draft_result, review_result, chapter_id, story_state, chapter_num):
    from packages.agents.src import committer
    return committer.run_committer(
        draft_result["draft_text"],
        review_result,
        chapter_id,
        story_state,
        chapter_num
    )


def _apply_state_diff(repo, project_id, chapter_id, chapter_num, commit_preview, draft_result, correlation_id: str = ""):
    """将 committer 产生的 state_diff 实际写入数据库。"""
    state_diff = commit_preview.get("state_diff", {})
    draft_text = draft_result["draft_text"]

    # 确保章节记录存在
    existing = repo.get_chapter(project_id, chapter_id)
    if not existing:
        repo.create_chapter(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter_num,
            title=""
        )
        existing = repo.get_chapter(project_id, chapter_id)

    # 写入章节内容（直接使用已读取的 existing 对象，避免重复查询）
    content_payload = {
        "draft_text": draft_text,
        "word_count": len(draft_text),
        "commit_preview": commit_preview
    }
    repo.save_chapter_content_unchecked(existing, content_payload, word_count=len(draft_text))

    # 更新章节状态为 committed（直接使用已读取的 existing 对象）
    repo.update_chapter_state_unchecked(existing, "committed")

    # 将本章摘要追加到 StoryState.chapters_json（供下一章上下文）
    story = repo.get_project(project_id)
    existing_chapters = story.get_chapters()
    existing_ids = {c["chapter_id"] for c in existing_chapters}
    for op in state_diff.get("add", []):
        if op.get("type") == "chapter_summary":
            op_chapter_id = op["chapter_id"]
            if op_chapter_id in existing_ids:
                # 去重：更新已有记录而非追加
                for ec in existing_chapters:
                    if ec["chapter_id"] == op_chapter_id:
                        ec.update({
                            "chapter_number": op["chapter_number"],
                            "summary": op["summary"],
                            "word_count": op["word_count"],
                            "state": op.get("state", "committed")
                        })
                        break
            else:
                existing_chapters.append({
                    "chapter_id": op_chapter_id,
                    "chapter_number": op["chapter_number"],
                    "summary": op["summary"],
                    "word_count": op["word_count"],
                    "state": op.get("state", "committed")
                })
                existing_ids.add(op_chapter_id)
    repo.update_story_state_chapters(project_id, existing_chapters)

    # 写入章节摘要事件
    repo.append_event(
        project_id=project_id,
        event_type="chapter.state_changed",
        actor_type="system",
        correlation_id=correlation_id,
        causation_id="",
        payload={
            "chapter_id": chapter_id,
            "chapter_number": chapter_num,
            "new_state": "committed",
            "word_count": len(draft_text)
        }
    )


def _advance_story_state(state: dict, chapter_result: dict):
    """将本章结果累计到 story_state，供下一章作上下文。"""
    commit_preview = chapter_result["commit_preview"]
    state_diff = commit_preview.get("state_diff", {})

    for op in state_diff.get("add", []):
        if op.get("type") == "chapter_summary":
            state.setdefault("chapters", []).append({
                "chapter_id": op["chapter_id"],
                "chapter_number": op["chapter_number"],
                "summary": op["summary"],
                "word_count": op["word_count"],
                "state": op.get("state", "committed")
            })
