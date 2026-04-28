import json
from packages.agents.src.base import ClaudeClient, load_prompt
from packages.agents.src.schema_validator import validate_payload


DEFAULT_REVIEWER_SYSTEM = """你是一个专业的小说审查员 Agent。你的任务是审查章节草稿的一致性、风格和追读力。

输出必须是有效的 JSON，格式如下：
{
  "consistency_issues": [
    {"type": "string", "location": "string", "description": "string", "severity": "critical|major|minor"}
  ],
  "style_issues": [
    {"type": "string", "location": "string", "description": "string", "severity": "critical|major|minor"}
  ],
  "readability_score": 0-100,
  "hook_strength_score": 0-100,
  "actionable_suggestions": [
    {"type": "hook|pace|character|style|consistency", "message": "string", "location": "string"}
  ],
  "risk_level": "low|medium|high"
}

重要规则：
- 一致性：角色设定、已建立的世界观规则是否被遵守
- 追读力：章节末是否有钩子、节奏是否紧凑
- 风格：去AI腔、对话自然、叙述生动
- 可执行建议：每个建议必须可以直接转化为改写动作
- **只输出纯 JSON**，不要使用 markdown 代码块包裹，不要有 ``` 符号
"""

REVIEWER_SYSTEM = load_prompt("reviewer_system") or DEFAULT_REVIEWER_SYSTEM


def run_reviewer(draft_text: str, story_state: dict, planner_output: dict) -> dict:
    client = ClaudeClient()

    context = f"""章节目标: {planner_output.get('chapter_goal', '')}
情节节奏: {json.dumps(planner_output.get('beats', []), ensure_ascii=False)}
角色设定: {json.dumps(story_state.get('characters', [])[:3], ensure_ascii=False)}
已有钩子: {json.dumps(story_state.get('hooks', [])[:3], ensure_ascii=False)}"""

    user_prompt = f"""请审查以下章节草稿：

{context}

章节草稿:
{draft_text[:4000]}

输出 JSON。"""

    response = client.generate(REVIEWER_SYSTEM, user_prompt, max_tokens=4096, agent_type="reviewer")
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        result = {
            "consistency_issues": [],
            "style_issues": [],
            "readability_score": 70,
            "hook_strength_score": 65,
            "actionable_suggestions": [],
            "risk_level": "medium"
        }

    valid, err = validate_payload(result, "agent_io/reviewer_output.schema.json")
    if not valid:
        raise ValueError(f"Reviewer output validation failed: {err}")

    return result
