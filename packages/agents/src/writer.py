import json
from packages.agents.src.base import ClaudeClient, load_prompt
from packages.agents.src.schema_validator import validate_payload


DEFAULT_WRITER_SYSTEM = """你是一个专业的小说写作者 Agent。你的任务是根据规划生成完整的章节草稿。

输出必须是有效的 JSON，格式如下：
{
  "draft_text": "string - 完整的章节草稿（中文，1000字以上）",
  "used_hooks": ["string - 本章激活的钩子ID列表"],
  "used_cards": ["string - 本章引用的卡片ID列表"],
  "open_questions": ["string - 本章遗留的问题或未完成的事项"]
}

重要规则：
- 严格按 beats 顺序推进情节
- 角色言行必须与已有设定一致
- 激活钩子时要有明确的文字对应
- 章节结尾要有钩子（悬念或伏笔）
- 避免AI腔：用自然的对话和叙述，避免过度解释
- **只输出纯 JSON**，不要使用 markdown 代码块包裹，不要有 ``` 符号
"""

WRITER_SYSTEM = load_prompt("writer_system") or DEFAULT_WRITER_SYSTEM


def run_writer(planner_output: dict, story_state: dict, chapter_num: int) -> dict:
    client = ClaudeClient()

    context = f"""当前章节号: {chapter_num}
章节目标: {planner_output.get('chapter_goal', '')}
情节节奏: {json.dumps(planner_output.get('beats', []), ensure_ascii=False)}
角色设定: {json.dumps(story_state.get('characters', [])[:3], ensure_ascii=False, indent=2)}
风格约束: {json.dumps(story_state.get('style_constraints', []), ensure_ascii=False)}"""

    user_prompt = f"""请根据以下规划，生成完整的章节草稿：

{context}

输出 JSON。"""

    response = client.generate(WRITER_SYSTEM, user_prompt, max_tokens=8192, agent_type="writer")
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        result = {
            "draft_text": response[:3000],
            "used_hooks": [],
            "used_cards": [],
            "open_questions": []
        }

    valid, err = validate_payload(result, "agent_io/writer_output.schema.json")
    if not valid:
        raise ValueError(f"Writer output validation failed: {err}")

    return result
