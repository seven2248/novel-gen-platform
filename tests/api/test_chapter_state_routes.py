import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel

from services.api.app.main import create_app
from services.api.app.models.story_state import StoryState, ChapterState
from services.api.app.models.event_log import EventLog


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
    from services.api.app.routers import chapters, projects

    def _get_session():
        return session

    app = create_app()
    app.dependency_overrides[projects.get_session] = _get_session
    app.dependency_overrides[chapters.get_session] = _get_session
    return TestClient(app)


def test_patch_chapter_state_updates_chapter_status(client, session):
    # Setup: create project and chapter via repository
    from services.api.app.repositories.story_state_repository import StoryStateRepository
    repo = StoryStateRepository(session)
    repo.get_or_create_project("proj-1", title="Test Project")
    repo.create_chapter("proj-1", "ch-1", chapter_number=1, title="第一章")

    response = client.patch(
        "/projects/proj-1/chapters/ch-1/state",
        json={"state": "reviewing", "version": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chapter_id"] == "ch-1"
    assert body["state"] == "reviewing"
    assert body["version"] == 1


def test_patch_chapter_state_rejects_stale_version(client, session):
    from services.api.app.repositories.story_state_repository import StoryStateRepository
    repo = StoryStateRepository(session)
    repo.get_or_create_project("proj-1", title="Test Project")
    repo.create_chapter("proj-1", "ch-1", chapter_number=1, title="第一章")

    # First update succeeds
    r1 = client.patch(
        "/projects/proj-1/chapters/ch-1/state",
        json={"state": "reviewing", "version": 0},
    )
    assert r1.status_code == 200

    # Second update with stale version (0) is rejected
    response = client.patch(
        "/projects/proj-1/chapters/ch-1/state",
        json={"state": "committed", "version": 0},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "version_conflict"


def test_get_chapter_state(client, session):
    from services.api.app.repositories.story_state_repository import StoryStateRepository
    repo = StoryStateRepository(session)
    repo.get_or_create_project("proj-1", title="Test Project")
    repo.create_chapter("proj-1", "ch-1", chapter_number=1, title="第一章")

    response = client.get("/projects/proj-1/chapters/ch-1")
    assert response.status_code == 200
    body = response.json()
    assert body["chapter_id"] == "ch-1"
    assert body["state"] == "not_started"
    assert body["version"] == 0


def test_create_chapter(client, session):
    response = client.post(
        "/projects/proj-1/chapters",
        json={"chapter_id": "ch-1", "chapter_number": 1, "title": "第一章"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chapter_id"] == "ch-1"
    assert body["state"] == "not_started"


def test_get_project(client, session):
    from services.api.app.repositories.story_state_repository import StoryStateRepository
    repo = StoryStateRepository(session)
    repo.get_or_create_project("proj-1", title="Test Project", genre="fantasy", style="classical")

    response = client.get("/projects/proj-1")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "proj-1"
    assert body["title"] == "Test Project"
