from sqlmodel import SQLModel, Field
from typing import Optional
import json
from datetime import datetime


class StoryState(SQLModel, table=True):
    __tablename__ = "story_states"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True, unique=True)
    version: int = Field(default=1)
    title: str = ""
    genre: str = ""
    style: str = ""
    characters_json: str = "[]"
    relationships_json: str = "[]"
    hooks_json: str = "[]"
    resources_json: str = "[]"
    chapters_json: str = "[]"
    style_constraints_json: str = "[]"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def get_characters(self):
        return json.loads(self.characters_json)

    def set_characters(self, chars):
        self.characters_json = json.dumps(chars, ensure_ascii=False)

    def get_hooks(self):
        return json.loads(self.hooks_json)

    def set_hooks(self, hooks):
        self.hooks_json = json.dumps(hooks, ensure_ascii=False)

    def get_chapters(self):
        return json.loads(self.chapters_json)

    def set_chapters(self, chapters):
        self.chapters_json = json.dumps(chapters, ensure_ascii=False)

    def to_dict(self):
        return {
            "project_id": self.project_id,
            "version": self.version,
            "title": self.title,
            "genre": self.genre,
            "style": self.style,
            "characters": self.get_characters(),
            "hooks": self.get_hooks(),
            "chapters": self.get_chapters(),
            "style_constraints": json.loads(self.style_constraints_json),
        }


class ChapterState(SQLModel, table=True):
    __tablename__ = "chapter_states"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    chapter_id: str = Field(index=True)
    chapter_number: int = Field(default=1)
    title: str = ""
    summary: str = ""
    state: str = Field(default="not_started")
    version: int = Field(default=0)
    word_count: int = Field(default=0)
    content_json: str = "{}"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "chapter_id": self.chapter_id,
            "chapter_number": self.chapter_number,
            "title": self.title,
            "summary": self.summary,
            "state": self.state,
            "version": self.version,
            "word_count": self.word_count,
        }
