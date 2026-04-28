"""
Tests for GET /events query API.
"""
import pytest


@pytest.fixture
def events_client(client):
    """client already has all session overrides including events.get_session."""
    yield client


class TestEventQuery:
    def test_events_returns_list(self, events_client):
        # Create project first (required for event FK)
        events_client.post(
            "/projects/test-proj",
            json={"title": "Test", "genre": "fantasy"},
        )

        response = events_client.get("/events", params={"project_id": "test-proj"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_events_by_correlation_id(self, events_client, test_engine):
        """Events with a specific correlation_id are returned when filtered."""
        events_client.post(
            "/projects/test-proj-2",
            json={"title": "Test", "genre": "fantasy"},
        )

        # Directly insert events via repo (shares the test db)
        from sqlmodel import Session
        from services.api.app.repositories.story_state_repository import StoryStateRepository

        with Session(test_engine) as s:
            repo = StoryStateRepository(s)
            repo.append_event(
                project_id="test-proj-2",
                event_type="planner.completed",
                actor_type="agent",
                correlation_id="abc123",
                causation_id="",
                payload={"chapter_num": 1},
            )
            repo.append_event(
                project_id="test-proj-2",
                event_type="writer.completed",
                actor_type="agent",
                correlation_id="abc123",
                causation_id="abc123",
                payload={"chapter_num": 1},
            )
            repo.append_event(
                project_id="test-proj-2",
                event_type="reviewer.completed",
                actor_type="agent",
                correlation_id="xyz789",
                causation_id="xyz789",
                payload={"chapter_num": 1},
            )

        # Filter by correlation_id=abc123
        response = events_client.get(
            "/events",
            params={"project_id": "test-proj-2", "correlation_id": "abc123"},
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 2
        assert all(e["correlation_id"] == "abc123" for e in events)

    def test_events_have_correct_structure(self, events_client, test_engine):
        """Each event dict contains all required fields."""
        events_client.post(
            "/projects/test-proj-3",
            json={"title": "Test", "genre": "fantasy"},
        )

        from sqlmodel import Session
        from services.api.app.repositories.story_state_repository import StoryStateRepository

        with Session(test_engine) as s:
            repo = StoryStateRepository(s)
            repo.append_event(
                project_id="test-proj-3",
                event_type="planner.completed",
                actor_type="agent",
                correlation_id="def456",
                causation_id="",
                payload={"chapter_num": 2},
            )

        response = events_client.get(
            "/events",
            params={"project_id": "test-proj-3", "correlation_id": "def456"},
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1
        e = events[0]
        assert set(e.keys()) == {"id", "event_type", "actor_type", "correlation_id", "causation_id", "payload", "created_at"}
        assert e["event_type"] == "planner.completed"
        assert e["correlation_id"] == "def456"
        assert e["payload"]["chapter_num"] == 2

    def test_events_ordered_descending(self, events_client, test_engine):
        """Events are returned most-recent-first."""
        events_client.post(
            "/projects/test-proj-4",
            json={"title": "Test", "genre": "fantasy"},
        )

        from sqlmodel import Session
        from services.api.app.repositories.story_state_repository import StoryStateRepository

        with Session(test_engine) as s:
            repo = StoryStateRepository(s)
            for i in range(3):
                repo.append_event(
                    project_id="test-proj-4",
                    event_type=f"stage.{i}",
                    actor_type="agent",
                    correlation_id="seq001",
                    causation_id="",
                    payload={},
                )

        response = events_client.get(
            "/events",
            params={"project_id": "test-proj-4", "correlation_id": "seq001", "limit": 10},
        )
        events = response.json()
        assert len(events) == 3
        # Most recent first (stage.2 should be first)
        assert events[0]["event_type"] == "stage.2"
        assert events[2]["event_type"] == "stage.0"
