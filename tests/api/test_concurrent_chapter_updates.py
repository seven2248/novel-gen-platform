"""
Concurrency tests for StoryStateRepository optimistic locking.

Tests the scenario where two writers attempt to update the same chapter
with the same expected_version — only one should succeed.
"""
import pytest
from sqlmodel import Session
from services.api.app.models.story_state import ChapterState
from services.api.app.repositories.story_state_repository import StoryStateRepository


@pytest.fixture
def repo(session):
    return StoryStateRepository(session)


def _create_chapter(repo, project_id="proj-1", chapter_id="ch-1"):
    repo.create_chapter(
        project_id=project_id,
        chapter_id=chapter_id,
        chapter_number=1,
        title="Test Chapter",
    )


class TestOptimisticLock:
    """Verify that concurrent updates with the same version cause the second to fail."""

    def test_second_update_with_stale_version_fails(self, temp_db):
        """Simulate: both readers get version=0, first writer increments, second fails."""
        engine, _ = temp_db

        # Writer A reads the chapter
        with Session(engine) as session_a:
            repo_a = StoryStateRepository(session_a)
            _create_chapter(repo_a)
            ch_a = repo_a.get_chapter("proj-1", "ch-1")
            assert ch_a.version == 0

            # Writer A updates successfully
            updated_a, ok_a = repo_a.update_chapter_state(
                "proj-1", "ch-1", "drafting", expected_version=0
            )
            assert ok_a is True
            assert updated_a.version == 1
            assert updated_a.state == "drafting"

        # Writer B reads the same version (after A already committed)
        with Session(engine) as session_b:
            repo_b = StoryStateRepository(session_b)
            ch_b = repo_b.get_chapter("proj-1", "ch-1")
            assert ch_b.version == 1  # B sees A's write

            # Writer B tries to update with stale version=0 → must fail
            updated_b, ok_b = repo_b.update_chapter_state(
                "proj-1", "ch-1", "reviewing", expected_version=0
            )
            assert ok_b is False
            # State should be unchanged (still A's write)
            assert updated_b.version == 1
            assert updated_b.state == "drafting"

    def test_same_version_both_read_before_either_commit_stale(self, temp_db):
        """
        True concurrent read: both A and B read version=0 before either writes.
        When A commits first, B's subsequent update must see the version mismatch.
        """
        engine, _ = temp_db

        # Pre-populate chapter so both sessions can read it
        with Session(engine) as init_session:
            init_repo = StoryStateRepository(init_session)
            _create_chapter(init_repo)

        # Both A and B start transactions and read version=0
        with Session(engine) as session_a:
            repo_a = StoryStateRepository(session_a)
            ch_a = repo_a.get_chapter("proj-1", "ch-1")
            ver_a = ch_a.version

            with Session(engine) as session_b:
                repo_b = StoryStateRepository(session_b)
                ch_b = repo_b.get_chapter("proj-1", "ch-1")
                ver_b = ch_b.version
                assert ver_a == ver_b == 0

                # A commits first
                repo_a.update_chapter_state(
                    "proj-1", "ch-1", "drafting", expected_version=ver_a
                )

                # B tries with the version it read earlier
                updated_b, ok_b = repo_b.update_chapter_state(
                    "proj-1", "ch-1", "reviewing", expected_version=ver_b
                )
                assert ok_b is False
                assert updated_b.version == 1
                assert updated_b.state == "drafting"

    def test_concurrent_writes_same_target_state_both_return_false(self, temp_db):
        """
        Both A and B read version=0 simultaneously and both try to set the SAME state.
        The first writer commits; the second's UPDATE must hit 0 rows (rowcount=0)
        and correctly return False — even though the re-fetched state matches the
        target state that both writers requested.
        """
        engine, _ = temp_db

        # Pre-populate chapter so both sessions can read it
        with Session(engine) as init_session:
            init_repo = StoryStateRepository(init_session)
            _create_chapter(init_repo)

        # Both A and B start transactions and read version=0, state="not_started"
        with Session(engine) as session_a:
            repo_a = StoryStateRepository(session_a)
            ch_a = repo_a.get_chapter("proj-1", "ch-1")
            ver_a = ch_a.version
            state_a = ch_a.state
            assert ver_a == 0 and state_a == "not_started"

            with Session(engine) as session_b:
                repo_b = StoryStateRepository(session_b)
                ch_b = repo_b.get_chapter("proj-1", "ch-1")
                ver_b = ch_b.version
                assert ver_a == ver_b == 0

                # A writes first with expected_version=0
                updated_a, ok_a = repo_a.update_chapter_state(
                    "proj-1", "ch-1", "drafting", expected_version=ver_a
                )
                assert ok_a is True
                assert updated_a.version == 1
                assert updated_a.state == "drafting"

                # B tries to write the SAME state "drafting" with expected_version=0
                # B's UPDATE WHERE version=0 matches 0 rows (version is already 1)
                updated_b, ok_b = repo_b.update_chapter_state(
                    "proj-1", "ch-1", "drafting", expected_version=ver_b
                )
                # Must be False — B's UPDATE did not apply
                assert ok_b is False
                # The re-fetched state will be A's write (state="drafting"), which
                # coincidentally matches B's requested state — that MUST NOT fool us
                assert updated_b.state == "drafting"
                assert updated_b.version == 1

    def test_update_without_version_is_unguarded(self, temp_db):
        """Updates without expected_version bypass the lock (used by internal flows)."""
        engine, _ = temp_db

        with Session(engine) as session:
            repo = StoryStateRepository(session)
            _create_chapter(repo)

            # No expected_version → unguarded increment
            ch1, ok1 = repo.update_chapter_state("proj-1", "ch-1", "drafting")
            assert ok1 is True
            assert ch1.version == 1

            # Second unguarded update also succeeds
            ch2, ok2 = repo.update_chapter_state("proj-1", "ch-1", "reviewing")
            assert ok2 is True
            assert ch2.version == 2
            assert ch2.state == "reviewing"
