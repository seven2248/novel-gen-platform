"""
Tests for simple chapter retrieval: get_recent_chapters + injection into story_state.
"""
import pytest
from sqlmodel import Session
from services.api.app.repositories.story_state_repository import StoryStateRepository


@pytest.fixture
def repo(session):
    return StoryStateRepository(session)


class TestGetRecentChapters:
    def test_returns_only_committed_or_reviewing(self, repo):
        repo.create_chapter("proj", "ch-1", 1, "")
        repo.create_chapter("proj", "ch-2", 2, "")
        repo.create_chapter("proj", "ch-3", 3, "")

        # Update ch-1 to committed, ch-2 stays not_started
        repo.update_chapter_state("proj", "ch-1", "committed")
        # ch-3 is in reviewing
        repo.update_chapter_state("proj", "ch-3", "reviewing")

        recent = repo.get_recent_chapters("proj", limit=10)
        ids = [c["chapter_id"] for c in recent]
        assert "ch-1" in ids
        assert "ch-3" in ids
        # ch-2 is not_started, should not appear
        assert "ch-2" not in ids

    def test_respects_limit(self, repo):
        for i in range(1, 6):
            repo.create_chapter("proj", f"ch-{i}", i, "")
            repo.update_chapter_state("proj", f"ch-{i}", "committed")

        recent = repo.get_recent_chapters("proj", limit=3)
        assert len(recent) == 3
        # Most recent first (ch-5 is highest chapter_number)
        assert recent[0]["chapter_id"] == "ch-5"
        assert recent[2]["chapter_id"] == "ch-3"

    def test_returns_correct_fields(self, repo):
        from sqlmodel import update
        from services.api.app.models.story_state import ChapterState

        repo.create_chapter("proj", "ch-x", 1, "第一章标题")
        # Directly set summary and word_count via SQL update
        stmt = (
            update(ChapterState)
            .where(ChapterState.chapter_id == "ch-x")
            .values(summary="这是第一章摘要", word_count=1234)
        )
        repo.session.exec(stmt)
        repo.session.commit()
        repo.update_chapter_state("proj", "ch-x", "committed")

        recent = repo.get_recent_chapters("proj")
        assert len(recent) == 1
        ch = recent[0]
        assert set(ch.keys()) == {"chapter_id", "chapter_number", "title", "summary", "state", "word_count"}
        assert ch["chapter_id"] == "ch-x"
        assert ch["chapter_number"] == 1
        assert ch["title"] == "第一章标题"
        assert ch["summary"] == "这是第一章摘要"
        assert ch["state"] == "committed"
        assert ch["word_count"] == 1234
