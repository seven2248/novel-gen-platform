"""
测试 4-agent 章节生成流程
（mock 由 conftest.py autouse fixture 提供）
"""
import pytest


def test_planner_returns_structured_output(fake_story_state):
    from packages.agents.src import planner
    result = planner.run_planner("生成第1章", fake_story_state, 1)
    assert result["chapter_goal"] == "主角进入宗门修炼"
    assert len(result["beats"]) == 3
    assert "cards_attached" in result


def test_writer_returns_draft_text(fake_story_state):
    from packages.agents.src import writer
    plan = {"chapter_goal": "测试", "beats": ["第一步"], "required_hooks": []}
    result = writer.run_writer(plan, fake_story_state, 1)
    assert "draft_text" in result
    assert len(result["draft_text"]) > 50


def test_reviewer_returns_scores_and_suggestions(fake_story_state):
    from packages.agents.src import reviewer
    plan = {"chapter_goal": "测试", "beats": ["第一步"]}
    draft = "青云宗的山门高耸入云..."
    result = reviewer.run_reviewer(draft, fake_story_state, plan)
    assert result["readability_score"] == 78
    assert result["risk_level"] == "low"
    assert len(result["actionable_suggestions"]) == 1


def test_committer_produces_state_diff(fake_story_state):
    from packages.agents.src import committer
    draft = "测试章节内容" * 50
    review = {
        "readability_score": 75,
        "hook_strength_score": 70,
        "risk_level": "low",
        "used_hooks": []
    }
    result = committer.run_committer(draft, review, "ch-1", fake_story_state)
    assert "state_diff" in result
    assert "add" in result["state_diff"]
    assert len(result["state_diff"]["add"]) > 0
    assert result["state_diff"]["add"][0]["type"] == "chapter_summary"


def test_main_flow_returns_complete_output(fake_story_state):
    from packages.agents.src.main_flow import run_main_flow
    result = run_main_flow(fake_story_state, "生成第1章：主角进入宗门", chapter_num=1)
    assert "plan" in result
    assert "draft" in result
    assert "review" in result
    assert "commit_preview" in result
    assert result["correlation_id"]
    assert result["chapter_num"] == 1
    assert len(result["draft"]["draft_text"]) > 50
