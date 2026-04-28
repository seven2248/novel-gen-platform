import pytest
from pathlib import Path
import tempfile
import os
from sqlmodel import SQLModel, Session, create_engine


@pytest.fixture(autouse=True)
def mock_llm():
    """Enable mock LLM responses for all tests that call agent code."""
    from packages.agents.src.base import set_mock_responses, reset_mock, MOCK_RESPONSES
    set_mock_responses(MOCK_RESPONSES)
    yield
    reset_mock()


@pytest.fixture
def temp_db():
    # 导入模型以注册到 SQLModel.metadata
    from services.api.app.models.story_state import StoryState, ChapterState
    from services.api.app.models.event_log import EventLog

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    SQLModel.metadata.create_all(engine)
    yield engine, path
    engine.dispose()  # 关闭所有连接，Windows 上才能删除文件
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows 上文件可能被锁住，忽略即可


@pytest.fixture
def session(temp_db):
    engine, _ = temp_db
    with Session(engine) as s:
        yield s


@pytest.fixture
def fake_project():
    return {
        "id": "test-project-1",
        "title": "Test Novel",
        "genre": "fantasy",
        "style": "classical_chinese",
    }


@pytest.fixture
def fake_story_state():
    return {
        "title": "测试小说",
        "genre": "玄幻",
        "style": "古典",
        "characters": [
            {"id": "char-1", "name": "李明", "status": "alive", "location": "青云宗"}
        ],
        "hooks": [
            {"id": "hook-1", "type": "foreshadow", "status": "open", "chapter_introduced": 0}
        ],
        "chapters": [],
        "style_constraints": ["去AI腔"]
    }
