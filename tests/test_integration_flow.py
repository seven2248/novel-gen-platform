"""
集成测试：Story State Core 回写、事件日志、连续章节闭环

使用 sqlite + mock agent，确保在无外部 API 的情况下验证完整闭环。
"""
import pytest
import os
import tempfile
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

# 全局 mock（由 conftest.py 的 autouse fixture 提供）


class TestStoryStateCoreWriteback:
    """P0-1 验证：章节回写到 Story State Core"""

    def test_chapter_record_created_and_content_saved(self, temp_db, fake_story_state):
        from services.api.app.models.story_state import StoryState, ChapterState
        from services.api.app.models.event_log import EventLog
        from services.api.app.repositories.story_state_repository import StoryStateRepository
        from packages.agents.src.workflow import run_chapter_flow_with_db

        engine, _ = temp_db
        with Session(engine) as session:
            repo = StoryStateRepository(session)
            repo.get_or_create_project("proj-1", title="测试", genre="玄幻", style="古典")

            result = run_chapter_flow_with_db(
                repo=repo,
                project_id="proj-1",
                chapter_goal="生成第1章",
                story_state=fake_story_state,
                chapter_num=1,
                chapter_id="ch-1",
            )

            # 验证章节记录存在
            ch = repo.get_chapter("proj-1", "ch-1")
            assert ch is not None, "ChapterState 记录应该被创建"
            assert ch.state == "committed", f"章节状态应为 committed，实际: {ch.state}"
            assert ch.word_count > 0, "章节应该有字数"

            # 验证内容被保存
            assert ch.content_json != "{}", "章节内容 JSON 不应为空"

            # 验证 story_state 有一章记录
            story = repo.get_or_create_project("proj-1")
            chapters_in_story = story.get_chapters()
            assert len(chapters_in_story) >= 1, "StoryState.chapters 应至少含本章"


class TestEventLog:
    """P0-2 验证：事件日志在每个阶段被正确写入"""

    def test_events_logged_for_each_agent_stage(self, temp_db, fake_story_state):
        from services.api.app.models.event_log import EventLog
        from services.api.app.repositories.story_state_repository import StoryStateRepository
        from packages.agents.src.workflow import run_chapter_flow_with_db

        engine, _ = temp_db
        with Session(engine) as session:
            repo = StoryStateRepository(session)
            repo.get_or_create_project("proj-1", title="测试", genre="玄幻", style="古典")

            result = run_chapter_flow_with_db(
                repo=repo,
                project_id="proj-1",
                chapter_goal="生成第1章",
                story_state=fake_story_state,
                chapter_num=1,
                chapter_id="ch-1",
            )

            events = repo.get_events("proj-1", limit=50)
            event_types = [e.event_type for e in events]

            # 验证各阶段事件存在
            assert "planner.completed" in event_types, "应有 planner.completed 事件"
            assert "writer.completed" in event_types, "应有 writer.completed 事件"
            assert "reviewer.completed" in event_types, "应有 reviewer.completed 事件"
            assert "committer.previewed" in event_types, "应有 committer.previewed 事件"
            assert "chapter.state_changed" in event_types, "应有 chapter.state_changed 事件"

    def test_events_have_correct_correlation_chain(self, temp_db, fake_story_state):
        from services.api.app.repositories.story_state_repository import StoryStateRepository
        from packages.agents.src.workflow import run_chapter_flow_with_db

        engine, _ = temp_db
        with Session(engine) as session:
            repo = StoryStateRepository(session)
            repo.get_or_create_project("proj-1", title="测试", genre="玄幻", style="古典")

            result = run_chapter_flow_with_db(
                repo=repo,
                project_id="proj-1",
                chapter_goal="生成第1章",
                story_state=fake_story_state,
                chapter_num=1,
            )

            correlation_id = result["correlation_id"]
            events = repo.get_events("proj-1", limit=50)

            # 所有事件应有相同的 correlation_id
            for e in events:
                assert e.correlation_id == correlation_id, \
                    f"事件 {e.event_type} 的 correlation_id 应为 {correlation_id}，实际: {e.correlation_id}"


class TestContinuousChapterGeneration:
    """P1-1 验证：连续 3 章闭环，每章状态正确累计"""

    def test_three_chapters_all_committed(self, temp_db, fake_story_state):
        from services.api.app.models.story_state import ChapterState
        from services.api.app.repositories.story_state_repository import StoryStateRepository
        from packages.agents.src.workflow import generate_chapters

        engine, _ = temp_db
        with Session(engine) as session:
            repo = StoryStateRepository(session)
            repo.get_or_create_project("proj-1", title="测试", genre="玄幻", style="古典")

            results = generate_chapters(
                repo=repo,
                project_id="proj-1",
                chapter_goals=["生成第1章", "生成第2章", "生成第3章"],
                story_state=fake_story_state,
                start_num=1,
            )

            # 验证生成了 3 章
            assert len(results) == 3, f"应生成 3 章，实际: {len(results)}"

            # 验证每章都 committed
            for i, r in enumerate(results):
                chapter_id = f"ch-{i+1}"
                ch = repo.get_chapter("proj-1", chapter_id)
                assert ch is not None, f"ch-{i+1} 记录应存在"
                assert ch.state == "committed", f"ch-{i+1} 状态应为 committed"

    def test_story_state_chapters_accumulates(self, temp_db, fake_story_state):
        from services.api.app.repositories.story_state_repository import StoryStateRepository
        from packages.agents.src.workflow import generate_chapters

        engine, _ = temp_db
        with Session(engine) as session:
            repo = StoryStateRepository(session)
            repo.get_or_create_project("proj-1", title="测试", genre="玄幻", style="古典")

            # 连续生成 3 章
            generate_chapters(
                repo=repo,
                project_id="proj-1",
                chapter_goals=["生成第1章", "生成第2章", "生成第3章"],
                story_state=fake_story_state,
                start_num=1,
            )

            # 验证 StoryState 累计了 3 章摘要
            story = repo.get_or_create_project("proj-1")
            chapters_in_story = story.get_chapters()
            assert len(chapters_in_story) == 3, \
                f"StoryState 应累计 3 章，实际: {len(chapters_in_story)}"

    def test_chapters_have_incrementing_numbers(self, temp_db, fake_story_state):
        from services.api.app.repositories.story_state_repository import StoryStateRepository
        from packages.agents.src.workflow import generate_chapters

        engine, _ = temp_db
        with Session(engine) as session:
            repo = StoryStateRepository(session)
            repo.get_or_create_project("proj-1", title="测试", genre="玄幻", style="古典")

            results = generate_chapters(
                repo=repo,
                project_id="proj-1",
                chapter_goals=["第1章内容", "第2章内容", "第3章内容"],
                story_state=fake_story_state,
                start_num=1,
            )

            for i, r in enumerate(results):
                assert r["chapter_num"] == i + 1, f"章节号应为 {i+1}"


class TestTruthFilesExport:
    """P2-3 验证：Truth Files 导出"""

    def test_chapters_md_exported_after_chapter_commit(self, temp_db, fake_story_state):
        import shutil
        from services.api.app.repositories.story_state_repository import StoryStateRepository
        from packages.agents.src.workflow import run_chapter_flow_with_db

        # 基于测试文件自身路径计算项目根目录，避免 namespace package __file__ 为 None 的问题
        project_root = Path(__file__).parent.parent
        truth_dir = project_root / "tests" / ".truth_test"
        if truth_dir.exists():
            shutil.rmtree(truth_dir)
        truth_dir.mkdir(parents=True)

        try:
            engine, _ = temp_db
            with Session(engine) as session:
                repo = StoryStateRepository(session)
                repo.get_or_create_project("proj-truth", title="测试", genre="玄幻", style="古典")

                result = run_chapter_flow_with_db(
                    repo=repo,
                    project_id="proj-truth",
                    chapter_goal="生成测试章节",
                    story_state=fake_story_state,
                    chapter_num=1,
                    chapter_id="ch-1",
                    truth_output_dir=truth_dir,
                )

                chapters_md = truth_dir / "chapters.md"
                assert chapters_md.exists(), f"chapters.md 应存在: {chapters_md}"

                content = chapters_md.read_text(encoding="utf-8")
                assert "第 1 章" in content, "chapters.md 应包含章节号"
                assert "committed" in content, "chapters.md 应包含状态"
        finally:
            if truth_dir.exists():
                shutil.rmtree(truth_dir, ignore_errors=True)
