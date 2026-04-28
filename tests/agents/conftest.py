import pytest


@pytest.fixture(autouse=True)
def mock_agents():
    """Enable mock responses for all agent tests."""
    from packages.agents.src.base import set_mock_responses, reset_mock, MOCK_RESPONSES
    set_mock_responses(MOCK_RESPONSES)
    yield
    reset_mock()
