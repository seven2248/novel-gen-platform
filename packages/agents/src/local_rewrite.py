"""
本地改写快车道：selected text → local context → local write → diff → commit preview

高频精修专用链路，不走全章生成，独立于主流程。
"""
import difflib
import json
import uuid

from packages.agents.src.base import ClaudeClient
from packages.agents.src.schema_validator import validate_payload


LOCAL_WRITER_SYSTEM = """你是一个专业的小说精修 Agent。你的任务是在已有章节上下文中，对用户选定的文本片段进行高质量改写。

输入：
- selected_text: 用户选定的待改写片段
- context: 周围上下文（前后各一段）
- story_state: 当前故事状态
- rewrite_instructions: 改写要求（如"加强情感张力"、"调整节奏"）

输出必须是有效的 JSON，格式如下：
{
  "rewritten_text": "string - 改写后的文本片段",
  "change_summary": "string - 改写内容摘要（10字内）",
  "tone_shift": "string - 语调变化描述",
  "risks": ["string - 潜在风险列表"]
}

重要规则：
- 保持与上下文的一致性（角色名、语气、节奏）
- 改写幅度适中，不要颠覆原文核心
- 如果选段是对话，保持对话自然
- 避免AI腔：用词自然，不过度解释
- **只输出纯 JSON**，不要使用 markdown 代码块包裹，不要有 ``` 符号
"""


def run_local_rewrite(
    selected_text: str,
    context_before: str,
    context_after: str,
    story_state: dict,
    rewrite_instructions: str = "",
    chapter_id: str = "unknown"
) -> dict:
    """
    本地改写流程。

    Args:
        selected_text: 用户选定的待改写片段
        context_before: 选段前的上下文
        context_after: 选段后的上下文
        story_state: 当前故事状态
        rewrite_instructions: 改写要求（可选）
        chapter_id: 章节 ID（用于追踪）

    Returns:
        {
            "rewritten_text": str,
            "change_summary": str,
            "tone_shift": str,
            "risks": list,
            "diff_lines": list,  # unified diff 行列表
            "correlation_id": str
        }
    """
    client = ClaudeClient()
    correlation_id = str(uuid.uuid4())[:8]

    characters = story_state.get("characters", [])
    recent_chapters = story_state.get("chapters", [])[-2:]

    context = f"""【周围上文】
{context_before}

【待改写片段】
{selected_text}

【周围下文】
{context_after}

【当前出场角色】
{chr(10).join(c.get('name', '') for c in characters[:3]) if characters else '（无）'}

【已有章节摘要】
{chr(10).join(f"第{c.get('chapter_number', '?')}章: {c.get('summary', '')[:50]}" for c in recent_chapters) if recent_chapters else '（无）'}

【改写要求】
{rewrite_instructions or '保持原文风格，优化表达'}

请生成改写结果 JSON。"""

    response = client.generate(LOCAL_WRITER_SYSTEM, context, max_tokens=2048, agent_type="writer")

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        result = {
            "rewritten_text": selected_text,
            "change_summary": "改写失败，保留原文",
            "tone_shift": "无变化",
            "risks": ["JSON 解析失败"]
        }

    valid, err = validate_payload(result, "agent_io/local_rewrite_output.schema.json")
    if not valid:
        result = {
            "rewritten_text": selected_text,
            "change_summary": "验证失败，保留原文",
            "tone_shift": "无变化",
            "risks": [f"Schema 验证失败: {err}"]
        }

    # 生成 diff
    diff_lines = list(difflib.unified_diff(
        selected_text.splitlines(keepends=True),
        result["rewritten_text"].splitlines(keepends=True),
        fromfile=f"a/{chapter_id}",
        tofile=f"b/{chapter_id}",
        lineterm=""
    ))

    return {
        **result,
        "diff_lines": diff_lines,
        "correlation_id": correlation_id
    }


def assemble_local_context(chapter_content: str, selection_start: int, selection_end: int, context_chars: int = 300) -> dict:
    """
    从章节内容中提取本地改写所需的上下文。

    Args:
        chapter_content: 完整章节内容
        selection_start: 选段起始位置（字符偏移）
        selection_end: 选段结束位置（字符偏移）
        context_chars: 上下文字符数

    Returns:
        {
            "selected_text": str,
            "context_before": str,
            "context_after": str
        }
    """
    before = chapter_content[max(0, selection_start - context_chars):selection_start]
    selected = chapter_content[selection_start:selection_end]
    after = chapter_content[selection_end:selection_end + context_chars]

    return {
        "selected_text": selected,
        "context_before": before,
        "context_after": after
    }
