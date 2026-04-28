import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel

from services.api.app.main import create_app
from services.api.app.models.story_state import StoryState, ChapterState
from services.api.app.models.event_log import EventLog
from services.api.app.routers import chapters, events, projects
from packages.agents.src.base import set_mock_responses, reset_mock, MOCK_RESPONSES
from tests.conftest import fake_story_state  # noqa: F401


@pytest.fixture(autouse=True)
def _mock_llm():
    """Scope to tests/api/ only — ensures API route tests never hit live endpoints."""
    set_mock_responses(MOCK_RESPONSES)
    yield
    reset_mock()


@pytest.fixture
def test_engine():
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine):
    with Session(test_engine) as s:
        yield s


@pytest.fixture
def client(session):
    def _get_session():
        return session

    app = create_app()
    app.dependency_overrides[projects.get_session] = _get_session
    app.dependency_overrides[chapters.get_session] = _get_session
    app.dependency_overrides[events.get_session] = _get_session
    return TestClient(app)
