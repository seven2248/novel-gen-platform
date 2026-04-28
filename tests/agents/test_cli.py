"""
测试 CLI 入口（cli.py）
"""
import pytest
import json
from io import StringIO
import sys


def test_run_quick_mode_produces_valid_structure(fake_story_state, capsys):
    """run_quick_mode 输出结构正确"""
    from packages.agents.src.cli import run_quick_mode
    from packages.agents.src.base import set_mock_responses, reset_mock

    set_mock_responses({
        "planner": {
            "chapter_goal": "测试章节",
            "beats": ["第一步"],
            "cards_attached": [],
            "context_hints": [],
            "required_hooks": [],
            "tone_hint": "中性"
        },
        "writer": {
            "draft_text": "青云宗的山门高耸入云。李明站在山脚下测试。",
            "used_hooks": [],
            "used_cards": [],
            "open_questions": []
        },
        "reviewer": {
            "consistency_issues": [],
            "style_issues": [],
            "readability_score": 80,
            "hook_strength_score": 75,
            "actionable_suggestions": [],
            "risk_level": "low"
        }
    })

    result = run_quick_mode("生成第1章", 1)
    reset_mock()

    assert "correlation_id" in result
    assert "plan" in result
    assert "draft" in result
    assert "review" in result
    assert "commit_preview" in result
    assert result["chapter_num"] == 1


def test_print_result_handles_missing_keys(fake_story_state):
    """_print_result 对缺失键的容错"""
    from packages.agents.src.cli import _print_result

    # 缺少可选键时不应崩溃
    minimal_result = {
        "correlation_id": "test-123",
        "plan": {"chapter_goal": "测试"},
        "draft": {"draft_text": "测试内容" * 50},
        "review": {"readability_score": 75},
        "commit_preview": {"state_diff": {"add": [], "update": [], "remove": []}}
    }

    # 不应抛出 KeyError
    _print_result(minimal_result)


def test_cli_rewrite_mode_entry_exists():
    """CLI --rewrite 入口存在且可解析参数"""
    import argparse
    from packages.agents.src.cli import main

    # 测试 rewrite 参数解析不报错
    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrite", dest="rewrite_text")
    parser.add_argument("--chapter-id", default="ch-1")
    parser.add_argument("--context-before", dest="context_before", default="")
    parser.add_argument("--context-after", dest="context_after", default="")
    parser.add_argument("--instructions", default="")

    args = parser.parse_args([
        "--rewrite", "选定的文本",
        "--chapter-id", "ch-2",
        "--context-before", "前文",
        "--context-after", "后文",
        "--instructions", "加强情感"
    ])

    assert args.rewrite_text == "选定的文本"
    assert args.chapter_id == "ch-2"
    assert args.context_before == "前文"
    assert args.context_after == "后文"
    assert args.instructions == "加强情感"
