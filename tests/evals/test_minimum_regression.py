import pytest
from evals.run_minimum_regression import load_suite


def test_minimum_regression_suite_contains_required_checks():
    suite = load_suite("evals/cases/minimum_set.yaml")
    assert len(suite["cases"]) >= 3
    assert "hook_presence" in suite["cases"][0]["checks"]
    assert "min_word_count" in suite["cases"][0]["checks"]


def test_story_constraint_scorer_flags_short_draft():
    from evals.scorers.story_constraints import score_story_constraints

    result = score_story_constraints(
        draft_text="太短了。",
        checks={"min_word_count": 100, "hook_presence": True},
    )
    assert result["passed"] is False
    assert "min_word_count" in result["failures"]


def test_story_constraint_scorer_passes_valid_draft():
    from evals.scorers.story_constraints import score_story_constraints

    result = score_story_constraints(
        draft_text="青云宗的山门高耸入云。李明站在山脚下，深吸一口气。师父说过，只有通过入门考验，才能真正踏入修行之路。石阶尽头，隐约可见一座宏伟的山门！",
        checks={"min_word_count": 50, "hook_presence": True},
    )
    assert result["passed"] is True


def test_story_constraint_scorer_flags_forbidden_pattern():
    from evals.scorers.story_constraints import score_story_constraints

    result = score_story_constraints(
        draft_text="请注意，以下是本章内容。师父看了他一眼，没有说话。",
        checks={"no_forbidden_patterns": True, "forbidden_patterns": ["请注意", "以下是"]},
    )
    assert result["passed"] is False
    assert any("forbidden_pattern" in f for f in result["failures"])
