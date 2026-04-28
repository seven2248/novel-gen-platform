"""
测试本地改写链路（local_rewrite.py）
"""
import pytest


def test_assemble_local_context_basic():
    """测试上下文组装基本功能"""
    from packages.agents.src.local_rewrite import assemble_local_context

    content = "这是第一章的内容。" * 100
    result = assemble_local_context(content, 50, 80, context_chars=20)

    assert result["selected_text"] == content[50:80]
    assert len(result["context_before"]) <= 20
    assert len(result["context_after"]) <= 20


def test_assemble_local_context_edge_cases():
    """边界情况：选择内容在文首或文尾"""
    from packages.agents.src.local_rewrite import assemble_local_context

    content = "短文"
    r1 = assemble_local_context(content, 0, 1, context_chars=10)
    assert r1["context_before"] == ""
    assert r1["selected_text"] == "短"

    r2 = assemble_local_context(content, 2, 3, context_chars=10)
    assert r2["context_after"] == ""


def test_run_local_rewrite_with_mock(fake_story_state):
    """测试 run_local_rewrite 返回正确结构"""
    from packages.agents.src.local_rewrite import run_local_rewrite
    from packages.agents.src.base import set_mock_responses, reset_mock

    mock_resp = {
        "writer": {
            "rewritten_text": "改写后的文本",
            "change_summary": "加强情感",
            "tone_shift": "更紧张",
            "risks": []
        }
    }
    set_mock_responses(mock_resp)

    result = run_local_rewrite(
        selected_text="原文",
        context_before="前文",
        context_after="后文",
        story_state=fake_story_state,
        rewrite_instructions="加强情感",
        chapter_id="ch-1"
    )

    reset_mock()

    assert "rewritten_text" in result
    assert "diff_lines" in result
    assert "correlation_id" in result
    assert "change_summary" in result


def test_run_local_rewrite_invalid_json_strict(fake_story_state):
    """非对象 JSON（字符串）触发 schema 验证失败 fallback"""
    from packages.agents.src.local_rewrite import run_local_rewrite
    from packages.agents.src.base import set_mock_responses, reset_mock

    # 字符串是合法 JSON，但不是对象，schema 验证失败 -> fallback
    set_mock_responses({"writer": "这不是 JSON 格式"})
    result = run_local_rewrite("原文", "", "", fake_story_state, "")
    reset_mock()

    # fallback 到原文，risks 包含验证失败信息
    assert result["rewritten_text"] == "原文"
    assert len(result["risks"]) > 0  # 验证失败进入 risks


def test_diff_generated_when_text_changes():
    """文本变化时生成 unified diff"""
    from packages.agents.src.local_rewrite import run_local_rewrite
    from packages.agents.src.base import set_mock_responses, reset_mock

    set_mock_responses({
        "writer": {
            "rewritten_text": "改写后内容",
            "change_summary": "修改",
            "tone_shift": "无",
            "risks": []
        }
    })

    result = run_local_rewrite("原文", "", "", {}, "")
    reset_mock()

    assert isinstance(result["diff_lines"], list)
