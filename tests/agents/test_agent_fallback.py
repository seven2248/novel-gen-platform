"""
测试 Agent 的 fallback 和错误处理路径
"""
import pytest


def test_planner_schema_validation_failure_raises(fake_story_state):
    """Planner 返回有效 JSON 但 schema 验证失败时抛出 ValueError"""
    from packages.agents.src import planner
    from packages.agents.src.base import set_mock_responses, reset_mock

    # schema 验证会失败（缺少 required 字段）
    set_mock_responses({"planner": {"chapter_goal": "测试"}})  # 缺 beats 等字段
    with pytest.raises(ValueError, match="validation failed"):
        planner.run_planner("生成第1章", fake_story_state, 1)
    reset_mock()


def test_writer_schema_validation_failure_raises(fake_story_state):
    """Writer 返回有效 JSON 但 schema 验证失败时抛出 ValueError"""
    from packages.agents.src import writer
    from packages.agents.src.base import set_mock_responses, reset_mock

    plan = {"chapter_goal": "测试", "beats": ["第一步"], "required_hooks": []}
    set_mock_responses({"writer": {"draft_text": ""}})  # minLength=1，空字符串失败
    with pytest.raises(ValueError, match="validation failed"):
        writer.run_writer(plan, fake_story_state, 1)
    reset_mock()


def test_reviewer_schema_validation_failure_raises(fake_story_state):
    """Reviewer 返回有效 JSON 但 schema 验证失败时抛出 ValueError"""
    from packages.agents.src import reviewer
    from packages.agents.src.base import set_mock_responses, reset_mock

    plan = {"chapter_goal": "测试", "beats": ["第一步"]}
    set_mock_responses({"reviewer": {"readability_score": 80}})  # 缺 required 字段
    with pytest.raises(ValueError, match="validation failed"):
        reviewer.run_reviewer("草稿内容", fake_story_state, plan)
    reset_mock()


def test_committer_high_risk_warning(fake_story_state):
    """Committer 高风险审查时的警告"""
    from packages.agents.src import committer

    draft = "测试章节内容" * 50
    review = {
        "readability_score": 40,
        "hook_strength_score": 30,
        "risk_level": "high",
        "used_hooks": []
    }
    result = committer.run_committer(draft, review, "ch-1", fake_story_state)

    assert "warnings" in result
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["type"] == "high_risk"


def test_planner_empty_story_state():
    """Planner 处理空 story_state（无 characters/chapters/hooks）"""
    from packages.agents.src import planner
    from packages.agents.src.base import set_mock_responses, reset_mock

    set_mock_responses({
        "planner": {
            "chapter_goal": "测试章节",
            "beats": ["第一步"],
            "cards_attached": [],
            "context_hints": [],
            "required_hooks": [],
            "tone_hint": "中性"
        }
    })
    empty_state = {"title": "测试"}
    result = planner.run_planner("生成第1章", empty_state, 1)
    reset_mock()

    assert "chapter_goal" in result
    assert "beats" in result


def test_writer_empty_story_state():
    """Writer 处理空 story_state"""
    from packages.agents.src import writer
    from packages.agents.src.base import set_mock_responses, reset_mock

    plan = {"chapter_goal": "测试", "beats": ["第一步"], "required_hooks": []}
    set_mock_responses({
        "writer": {
            "draft_text": "生成的草稿",
            "used_hooks": [],
            "used_cards": [],
            "open_questions": []
        }
    })
    empty_state = {"title": "测试"}
    result = writer.run_writer(plan, empty_state, 1)
    reset_mock()

    assert "draft_text" in result


def test_reviewer_empty_story_state():
    """Reviewer 处理空 story_state"""
    from packages.agents.src import reviewer
    from packages.agents.src.base import set_mock_responses, reset_mock

    plan = {"chapter_goal": "测试", "beats": ["第一步"]}
    set_mock_responses({
        "reviewer": {
            "consistency_issues": [],
            "style_issues": [],
            "readability_score": 80,
            "hook_strength_score": 75,
            "actionable_suggestions": [],
            "risk_level": "low"
        }
    })
    empty_state = {}
    result = reviewer.run_reviewer("草稿内容", empty_state, plan)
    reset_mock()

    assert "readability_score" in result
    assert result["risk_level"] == "low"


def test_advance_story_state_missing_chapters():
    """_advance_story_state 处理缺失 chapters 键"""
    from packages.agents.src.workflow import _advance_story_state

    state = {"title": "测试"}
    chapter_result = {
        "commit_preview": {
            "state_diff": {
                "add": [
                    {
                        "type": "chapter_summary",
                        "chapter_id": "ch-1",
                        "chapter_number": 1,
                        "summary": "测试摘要",
                        "word_count": 100,
                        "state": "committed"
                    }
                ],
                "update": [],
                "remove": []
            }
        }
    }

    _advance_story_state(state, chapter_result)
    assert "chapters" in state
    assert len(state["chapters"]) == 1
