from sqlmodel import Session, select, update
from services.api.app.models.story_state import StoryState, ChapterState
from services.api.app.models.event_log import EventLog
import json
from datetime import datetime, timezone


class StoryStateRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_project(self, project_id: str) -> StoryState | None:
        """Read-only project lookup — returns None if not found, never creates."""
        return self.session.exec(select(StoryState).where(StoryState.project_id == project_id)).first()

    def upsert_project(self, project_id: str, title: str = "", genre: str = "", style: str = "") -> StoryState:
        """Create or update a project. If project exists, update its fields."""
        state = self.get_project(project_id)
        if state is None:
            state = StoryState(project_id=project_id, title=title, genre=genre, style=style)
            self.session.add(state)
            self.session.commit()
            self.session.refresh(state)
        else:
            # Update existing fields — only override if non-empty values are provided
            if title:
                state.title = title
            if genre:
                state.genre = genre
            if style:
                state.style = style
            state.updated_at = datetime.now(timezone.utc).isoformat()
            self.session.commit()
            self.session.refresh(state)
        return state

    def get_or_create_project(self, project_id: str, title: str = "", genre: str = "", style: str = "") -> StoryState:
        state = self.session.exec(select(StoryState).where(StoryState.project_id == project_id)).first()
        if not state:
            state = StoryState(project_id=project_id, title=title, genre=genre, style=style)
            self.session.add(state)
            self.session.commit()
            self.session.refresh(state)
        return state

    def get_chapter(self, project_id: str, chapter_id: str) -> ChapterState | None:
        return self.session.exec(select(ChapterState).where(
            ChapterState.project_id == project_id,
            ChapterState.chapter_id == chapter_id
        )).first()

    def get_recent_chapters(self, project_id: str, limit: int = 5) -> list[dict]:
        """
        Return the most recent `limit` chapter summaries ordered by chapter_number desc.
        Each entry contains chapter_id, chapter_number, title, summary, state, word_count.
        """
        chapters = self.session.exec(
            select(ChapterState)
            .where(
                ChapterState.project_id == project_id,
                ChapterState.state.in_(["committed", "reviewing"]),
            )
            .order_by(ChapterState.chapter_number.desc())
            .limit(limit)
        ).all()
        return [
            {
                "chapter_id": ch.chapter_id,
                "chapter_number": ch.chapter_number,
                "title": ch.title,
                "summary": ch.summary,
                "state": ch.state,
                "word_count": ch.word_count,
            }
            for ch in chapters
        ]

    def create_chapter(self, project_id: str, chapter_id: str, chapter_number: int, title: str = "") -> ChapterState:
        ch = ChapterState(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            title=title,
            state="not_started",
            version=0
        )
        self.session.add(ch)
        self.session.commit()
        self.session.refresh(ch)
        return ch

    def update_chapter_state(self, project_id: str, chapter_id: str, new_state: str, expected_version: int | None = None) -> tuple[ChapterState, bool]:
        if expected_version is not None:
            # Atomic UPDATE ... WHERE version = expected_version
            # Execute via session.exec() to get rowcount: 1 = my UPDATE hit,
            # 0 = another writer already changed the version (my UPDATE is lost).
            # The subsequent re-fetch is only for the return value, not for
            # confirmation — rowcount is the authoritative signal.
            stmt = (
                update(ChapterState)
                .where(
                    ChapterState.project_id == project_id,
                    ChapterState.chapter_id == chapter_id,
                    ChapterState.version == expected_version,
                )
                .values(
                    state=new_state,
                    version=ChapterState.version + 1,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
            )
            try:
                result = self.session.exec(stmt)
                rowcount = result.rowcount
                self.session.commit()
            except Exception:
                return None, False

            if rowcount == 0:
                ch = self.get_chapter(project_id, chapter_id)
                return ch, False
            ch = self.get_chapter(project_id, chapter_id)
            return ch, True
        else:
            # Unguarded update: fetch and mutate
            ch = self.get_chapter(project_id, chapter_id)
            if not ch:
                raise ValueError(f"Chapter {chapter_id} not found")
            ch.state = new_state
            ch.version += 1
            ch.updated_at = datetime.now(timezone.utc).isoformat()
            self.session.commit()
            self.session.refresh(ch)
            return ch, True

    def save_chapter_content(self, project_id: str, chapter_id: str, content: dict, version: int | None = None, word_count: int | None = None) -> ChapterState:
        ch = self.get_chapter(project_id, chapter_id)
        if not ch:
            raise ValueError(f"Chapter {chapter_id} not found")

        if version is not None and ch.version != version:
            return ch

        ch.content_json = json.dumps(content, ensure_ascii=False)
        if word_count is not None:
            ch.word_count = word_count
        ch.updated_at = datetime.now(timezone.utc).isoformat()
        self.session.commit()
        self.session.refresh(ch)
        return ch

    def append_event(self, project_id: str, event_type: str, actor_type: str = "agent",
                     correlation_id: str = "", causation_id: str = "", payload: dict = None) -> EventLog:
        event = EventLog(
            project_id=project_id,
            event_type=event_type,
            actor_type=actor_type,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload_json=json.dumps(payload or {}, ensure_ascii=False)
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def get_events(self, project_id: str, limit: int = 100):
        return self.session.exec(select(EventLog).where(
            EventLog.project_id == project_id
        ).order_by(EventLog.id.desc()).limit(limit)).all()

    def update_chapter_state_unchecked(self, chapter: "ChapterState", new_state: str) -> "ChapterState":
        """Update chapter state without re-fetching — caller already holds the chapter object."""
        chapter.state = new_state
        chapter.version += 1
        chapter.updated_at = datetime.now(timezone.utc).isoformat()
        self.session.commit()
        self.session.refresh(chapter)
        return chapter

    def save_chapter_content_unchecked(self, chapter: "ChapterState", content: dict, word_count: int | None = None) -> "ChapterState":
        """Save chapter content without re-fetching — caller already holds the chapter object."""
        chapter.content_json = json.dumps(content, ensure_ascii=False)
        if word_count is not None:
            chapter.word_count = word_count
        chapter.updated_at = datetime.now(timezone.utc).isoformat()
        self.session.commit()
        self.session.refresh(chapter)
        return chapter

    def update_story_state_chapters(self, project_id: str, chapters: list) -> StoryState:
        """将章节摘要列表写回 StoryState.chapters_json（供下一章上下文使用）。"""
        state = self.get_or_create_project(project_id)
        state.set_chapters(chapters)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        self.session.commit()
        self.session.refresh(state)
        return state
