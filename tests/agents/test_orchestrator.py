"""
测试 orchestrator 模块：状态机验证 + warning 聚合 + correlation_id 透传
（mock 由 conftest.py autouse fixture 提供）
"""

import pytest

from packages.agents.src.orchestrator import (
    validate_state_transition,
    run_orchestrator,
)


# ---------------------------------------------------------------------------
# validate_state_transition 测试
# ---------------------------------------------------------------------------


class TestValidateStateTransition:
    def test_forward_not_started_to_drafting(self):
        is_valid, reason = validate_state_transition("not_started", "drafting")
        assert is_valid is True
        assert reason == "forward"

    def test_forward_drafting_to_reviewing(self):
        is_valid, reason = validate_state_transition("drafting", "reviewing")
        assert is_valid is True
        assert reason == "forward"

    def test_forward_reviewing_to_committed(self):
        is_valid, reason = validate_state_transition("reviewing", "committed")
        assert is_valid is True
        assert reason == "forward"

    def test_backward_reviewing_to_drafting_allowed(self):
        """审稿后退回重写是允许的（forward 方向退回去）"""
        is_valid, reason = validate_state_transition("reviewing", "drafting")
        assert is_valid is True
        assert reason == "forward"

    def test_backward_committed_to_reviewing_allowed(self):
        """committed 后退到 reviewing 审稿是允许的"""
        is_valid, reason = validate_state_transition("committed", "reviewing")
        assert is_valid is True
        assert reason == "forward"

    def test_committed_to_drafting_requires_explicit_reset(self):
        """committed → drafting 必须 explicit_reset=True"""
        is_valid, reason = validate_state_transition(
            "committed", "drafting", explicit_reset=False
        )
        assert is_valid is False
        assert "explicit_reset" in reason

    def test_committed_to_drafting_with_explicit_reset_ok(self):
        """committed → drafting + explicit_reset=True 是允许的"""
        is_valid, reason = validate_state_transition(
            "committed", "drafting", explicit_reset=True
        )
        assert is_valid is True
        assert reason == "explicit_reset"

    def test_committed_to_not_started_rejected(self):
        """committed → not_started 是非法跳转"""
        is_valid, reason = validate_state_transition("committed", "not_started")
        assert is_valid is False
        assert "非法状态迁移" in reason

    def test_unknown_target_state_rejected(self):
        is_valid, reason = validate_state_transition("drafting", "ghost_state")
        assert is_valid is False
        assert "未知状态" in reason

    def test_new_chapter_any_valid_state(self):
        """新建章节（current_state 不在已知状态时）允许任意合法目标状态"""
        is_valid, reason = validate_state_transition("unknown_state", "drafting")
        assert is_valid is True
        assert reason == ""


# ---------------------------------------------------------------------------
# run_orchestrator 测试
# ---------------------------------------------------------------------------


class TestRunOrchestrator:
    def test_orchestrator_returns_warnings_field(self, fake_story_state):
        """W19: orchestrator 返回统一聚合的 warnings 列表"""
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
        )
        assert "warnings" in result
        assert isinstance(result["warnings"], list)

    def test_orchestrator_returns_correlation_id(self, fake_story_state):
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
        )
        assert "correlation_id" in result
    def test_orchestrator_correlation_id_in_each_agent_output(self, fake_story_state):
        """W19 Finding 1 fix: correlation_id 必须出现在每个 agent 的输出 dict 中"""
        cid = "test-cid-42"
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
            correlation_id=cid,
        )
        assert result["plan"]["correlation_id"] == cid, "planner 输出缺少 correlation_id"
        assert result["draft"]["correlation_id"] == cid, "writer 输出缺少 correlation_id"
        assert result["review"]["correlation_id"] == cid, "reviewer 输出缺少 correlation_id"
        assert result["commit_preview"]["correlation_id"] == cid, "committer 输出缺少 correlation_id"
        assert result["correlation_id"] == cid, "orchestrator 返回值缺少 correlation_id"


    def test_orchestrator_accepts_custom_correlation_id(self, fake_story_state):
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
            correlation_id="custom-id-42",
        )
        assert result["correlation_id"] == "custom-id-42"

    def test_orchestrator_returns_all_agent_outputs(self, fake_story_state):
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
        )
        assert "plan" in result
        assert "draft" in result
        assert "review" in result
        assert "commit_preview" in result

    def test_orchestrator_returns_state_transition_none(self, fake_story_state):
        """orchestrator 不做状态写回，state_transition 固定为 None"""
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
        )
        assert result["state_transition"] is None

    def test_orchestrator_chapter_id_auto_generated(self, fake_story_state):
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=3,
        )
        assert result["chapter_id"] == "ch-3"
        assert result["chapter_num"] == 3

    def test_orchestrator_chapter_id_passed_through(self, fake_story_state):
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_id="my-custom-ch",
            chapter_num=5,
        )
        assert result["chapter_id"] == "my-custom-ch"

    def test_warnings_from_reviewer_consistency_issues(self, fake_story_state):
        """Reviewer 的 consistency_issues 被转换为 warnings"""
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
        )
        # MOCK_RESPONSES 的 reviewer 没有 consistency_issues，
        # 所以这里只检查 warnings 字段存在且格式正确
        for w in result["warnings"]:
            assert "_source" in w

    def test_warnings_from_committer_high_risk(self, fake_story_state):
        """Committer 的 high risk_level warning 被加入"""
        result = run_orchestrator(
            story_state=fake_story_state,
            chapter_goal="生成第1章",
            chapter_num=1,
        )
        # MOCK 的 risk_level 是 low，不会有 high_risk warning
        # 只验证 warning 列表格式
        for w in result["warnings"]:
            assert "type" in w or "_source" in w


# ---------------------------------------------------------------------------
# main_flow 向后兼容测试
# ---------------------------------------------------------------------------


class TestMainFlowBackwardCompat:
    def test_main_flow_still_returns_expected_fields(self, fake_story_state):
        """确保 run_main_flow 仍然返回旧版调用方期望的字段"""
        from packages.agents.src.main_flow import run_main_flow

        result = run_main_flow(fake_story_state, "生成第1章", chapter_num=1)
        # 旧字段
        assert "plan" in result
        assert "draft" in result
        assert "review" in result
        assert "commit_preview" in result
        assert "correlation_id" in result
        assert "chapter_id" in result
        assert "chapter_num" in result
        # W19 新字段（向后兼容）
        assert "warnings" in result
        assert "state_transition" in result
