import json
from packages.agents.src.base import ClaudeClient, load_prompt
from packages.agents.src.schema_validator import validate_payload


DEFAULT_PLANNER_SYSTEM = """你是一个专业的小说规划师 Agent。你的任务是根据用户给定的章节目标、当前故事状态，生成结构化的章节规划。

输出必须是有效的 JSON，格式如下：
{
  "chapter_goal": "string - 章节核心目标",
  "beats": ["string - 章节情节点列表，按顺序排列"],
  "cards_attached": ["string - 引用的卡片ID列表"],
  "context_hints": ["string - 给写作者的上下文提示"],
  "required_hooks": ["string - 需要在本章激活的钩子ID"],
  "tone_hint": "string - 风格语调提示"
}

重要规则：
- beats 数量适中（3-8个），每个 beat 描述一个核心事件
- context_hints 帮助写作者理解本章在全局中的位置
- 不要重复已有的伏笔，优先激活未支付的钩子
- **只输出纯 JSON**，不要使用 markdown 代码块包裹，不要有 ``` 符号
"""

PLANNER_SYSTEM = load_prompt("planner_system") or DEFAULT_PLANNER_SYSTEM


def run_planner(chapter_goal: str, story_state: dict, chapter_num: int) -> dict:
    client = ClaudeClient()

    context = f"""当前章节号: {chapter_num}
故事标题: {story_state.get('title', '')}
已有角色: {json.dumps(story_state.get('characters', [])[:5], ensure_ascii=False)}
已有钩子(未支付): {json.dumps([h for h in story_state.get('hooks', []) if h.get('status') == 'open'][:3], ensure_ascii=False)}
已有章节摘要: {json.dumps(story_state.get('chapters', [])[-3:], ensure_ascii=False)}"""

    user_prompt = f"""章节目标: {chapter_goal}

{context}

请生成章节规划 JSON。"""

    response = client.generate(PLANNER_SYSTEM, user_prompt, agent_type="planner")
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        result = {
            "chapter_goal": chapter_goal,
            "beats": [response[:500]],
            "cards_attached": [],
            "context_hints": [],
            "required_hooks": [],
            "tone_hint": "中性"
        }

    valid, err = validate_payload(result, "agent_io/planner_output.schema.json")
    if not valid:
        raise ValueError(f"Planner output validation failed: {err}")

    return result
