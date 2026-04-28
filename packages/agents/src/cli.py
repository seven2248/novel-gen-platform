#!/usr/bin/env python3
"""
小说生成系统 CLI 入口

用法:
  # 快速模式（mock，不写数据库）
  python -m packages.agents.src.cli "生成第1章"

  # DB 模式（真实闭环，写入 SQLite）
  python -m packages.agents.src.cli "生成第1章" --db

  # 连续多章模式
  python -m packages.agents.src.cli "第1章" "第2章" "第3章" --db
"""
import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.agents.src.main_flow import run_main_flow


DEFAULT_STORY_STATE = {
    "title": "测试小说",
    "genre": "玄幻",
    "style": "古典",
    "characters": [
        {"id": "char-1", "name": "李明", "status": "alive", "location": "青云宗"},
        {"id": "char-2", "name": "师父", "status": "alive", "location": "青云宗"}
    ],
    "hooks": [
        {"id": "hook-1", "type": "foreshadow", "status": "open", "chapter_introduced": 0, "description": "李明身世之谜"}
    ],
    "chapters": [],
    "style_constraints": ["去AI腔", "对话自然"]
}


def run_quick_mode(chapter_goal: str, chapter_num: int):
    """不使用数据库的快速模式（mock）"""
    print(f"\n=== 小说生成系统 [快速模式] ===")
    print(f"章节目标: {chapter_goal}")
    print(f"章节号: {chapter_num}")

    result = run_main_flow(
        story_state=DEFAULT_STORY_STATE,
        chapter_goal=chapter_goal,
        chapter_num=chapter_num
    )

    _print_result(result)
    return result


def run_db_mode(project_id: str, chapter_goal: str, chapter_num: int):
    """使用数据库的真实闭环模式"""
    from sqlmodel import SQLModel, Session, create_engine
    from services.api.app.models.story_state import StoryState, ChapterState
    from services.api.app.models.event_log import EventLog
    from services.api.app.repositories.story_state_repository import StoryStateRepository
    from packages.agents.src.workflow import run_chapter_flow_with_db

    db_base = Path(os.environ.get("NOVEL_GEN_DB_DIR", Path.home() / ".novel-gen"))
    db_path = db_base / f"{project_id}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = StoryStateRepository(session)
        repo.get_or_create_project(project_id, title="测试小说", genre="玄幻", style="古典")

        print(f"\n=== 小说生成系统 [DB模式] ===")
        print(f"项目: {project_id}")
        print(f"章节目标: {chapter_goal}")
        print(f"章节号: {chapter_num}")
        print(f"数据库: {db_path}")

        result = run_chapter_flow_with_db(
            repo=repo,
            project_id=project_id,
            chapter_goal=chapter_goal,
            story_state=DEFAULT_STORY_STATE,
            chapter_num=chapter_num,
        )

        _print_result(result)

        if result.get("truth_export_warning"):
            print(f"\nWARNING: Truth Files 导出失败: {result['truth_export_warning']}")

        events = repo.get_events(project_id, limit=20)
        print(f"\n--- 事件日志 ({len(events)} 条) ---")
        for e in reversed(events):
            print(f"  [{e.event_type}] correlation={e.correlation_id} actor={e.actor_type}")

        return result


def run_multi_chapter_mode(project_id: str, chapter_goals: list[str]):
    """连续多章节模式"""
    from sqlmodel import SQLModel, Session, create_engine
    from services.api.app.models.story_state import StoryState, ChapterState
    from services.api.app.models.event_log import EventLog
    from services.api.app.repositories.story_state_repository import StoryStateRepository
    from packages.agents.src.workflow import generate_chapters

    db_base = Path(os.environ.get("NOVEL_GEN_DB_DIR", Path.home() / ".novel-gen"))
    db_path = db_base / f"{project_id}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = StoryStateRepository(session)
        repo.get_or_create_project(project_id, title="测试小说", genre="玄幻", style="古典")

        print(f"\n=== 小说生成系统 [连续章节模式] ===")
        print(f"项目: {project_id}")
        print(f"章节数: {len(chapter_goals)}")

        results = generate_chapters(
            repo=repo,
            project_id=project_id,
            chapter_goals=chapter_goals,
            story_state=DEFAULT_STORY_STATE,
            start_num=1,
        )

        for r in results:
            print(f"\n章节 {r['chapter_num']} 完成: {len(r['draft']['draft_text'])} 字")
            if r.get("truth_export_warning"):
                print(f"WARNING: Truth Files 导出失败: {r['truth_export_warning']}")

        events = repo.get_events(project_id, limit=100)
        print(f"\n--- 事件日志 ({len(events)} 条) ---")
        for e in reversed(events):
            print(f"  [{e.event_type}] correlation={e.correlation_id}")

        return results


def _print_result(result):
    try:
        print(f"\n--- Plan (correlation_id: {result['correlation_id']}) ---")
        print(json.dumps(result["plan"], ensure_ascii=False, indent=2))

        draft_text = result.get("draft", {}).get("draft_text", "[无草稿]")
        print(f"\n--- Draft ({len(draft_text)} 字) ---")
        print(draft_text[:500] + "..." if draft_text else "[空草稿]")

        review_score = result.get("review", {}).get("readability_score", "N/A")
        print(f"\n--- Review (追读力评分: {review_score}) ---")
        print(json.dumps(result.get("review", {}), ensure_ascii=False, indent=2))

        print(f"\n--- Commit Preview ---")
        print(json.dumps(result.get("commit_preview", {}), ensure_ascii=False, indent=2))
    except (KeyError, TypeError) as e:
        print(f"\n[警告] 结果打印失败: {e}")
        print("[原始结果]")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def run_rewrite_mode(selected_text: str, chapter_id: str, context_before: str, context_after: str, instructions: str):
    """本地改写模式"""
    from packages.agents.src.local_rewrite import run_local_rewrite, assemble_local_context

    print(f"\n=== 小说生成系统 [本地改写模式] ===")
    print(f"章节ID: {chapter_id}")

    if context_before or context_after:
        ctx = {
            "selected_text": selected_text,
            "context_before": context_before or "",
            "context_after": context_after or ""
        }
    else:
        print("注意: 未提供上下文，使用默认值（建议通过 --context-before 和 --context-after 提供）")
        ctx = {
            "selected_text": selected_text,
            "context_before": "",
            "context_after": ""
        }

    result = run_local_rewrite(
        selected_text=selected_text,
        context_before=ctx["context_before"],
        context_after=ctx["context_after"],
        story_state=DEFAULT_STORY_STATE,
        rewrite_instructions=instructions,
        chapter_id=chapter_id
    )

    print(f"\n--- 改写结果 ({len(result['rewritten_text'])} 字) ---")
    print(result["rewritten_text"])

    print(f"\n--- 变更摘要 ---")
    print(f"摘要: {result.get('change_summary', 'N/A')}")
    print(f"语调变化: {result.get('tone_shift', 'N/A')}")
    if result.get("risks"):
        print(f"风险: {', '.join(result['risks'])}")

    if result.get("diff_lines"):
        print(f"\n--- Diff ---")
        print("".join(result["diff_lines"]))

    return result


def main():
    parser = argparse.ArgumentParser(description="小说生成系统 CLI")
    parser.add_argument("goals", nargs="*", help="章节目标（支持多章）")
    parser.add_argument("--db", action="store_true", help="启用数据库模式（真实闭环）")
    parser.add_argument("--project-id", default="default-project", help="项目 ID（DB 模式必填）")
    # 本地改写
    parser.add_argument("--rewrite", dest="rewrite_text", metavar="TEXT", help="本地改写：待改写文本")
    parser.add_argument("--chapter-id", default="ch-1", help="章节 ID（改写模式用）")
    parser.add_argument("--context-before", dest="context_before", default="", help="选段前上下文")
    parser.add_argument("--context-after", dest="context_after", default="", help="选段后上下文")
    parser.add_argument("--instructions", default="", help="改写要求")
    args = parser.parse_args()

    # 本地改写模式
    if args.rewrite_text:
        run_rewrite_mode(
            args.rewrite_text,
            args.chapter_id,
            args.context_before,
            args.context_after,
            args.instructions
        )
        return

    if not args.goals:
        parser.print_help()
        return

    if args.db:
        if len(args.goals) == 1:
            run_db_mode(args.project_id, args.goals[0], 1)
        else:
            run_multi_chapter_mode(args.project_id, args.goals)
    else:
        if len(args.goals) == 1:
            run_quick_mode(args.goals[0], 1)
        else:
            print("快速模式不支持多章节，使用 --db 启用连续章节模式")
            sys.exit(1)


if __name__ == "__main__":
    main()
