"""
LLM Client — 基于 LiteLLM，支持 OpenAI / Anthropic / Gemini / DeepSeek 等多厂商

配置方式（环境变量）：
  OPENAI_API_KEY      — OpenAI 系模型
  ANTHROPIC_API_KEY   — Anthropic 系模型
  GEMINI_API_KEY      — Google Gemini
  DEEPSEEK_API_KEY    — DeepSeek
  # 其他厂商 key 见 https://docs.litellm.ai/docs/providers

模型路由（每个 Agent 可配不同厂商）：
  LLM_CONFIG 环境变量 JSON，格式：
  {
    "planner":   "openai/gpt-4o",
    "writer":    "openai/gpt-4o",
    "reviewer":  "anthropic/claude-sonnet-4-6-5-20251120",
    "committer": "deepseek/deepseek-chat-v3"
  }
  不配置时默认全部用 "openai/gpt-4o"
"""
import json
import os
from pathlib import Path
from litellm import completion


# ------------------------------------------------------------------
# Mock 状态（测试用）
# ------------------------------------------------------------------

_mock_state = {"enabled": False, "responses": {}}

MOCK_RESPONSES = {
    "planner": {
        "chapter_goal": "主角进入宗门修炼",
        "beats": ["主角到达山门", "通过入门考验", "拜入师门"],
        "cards_attached": [],
        "context_hints": ["本章是开局"],
        "required_hooks": [],
        "tone_hint": "热血"
    },
    "writer": {
        "draft_text": "青云宗的山门高耸入云。李明站在山脚下，仰望那层层叠叠的石阶，深吸一口气。师父说过，只有通过入门考验，才能真正踏入修行之路。石阶尽头，隐约可见一座宏伟的山门，门楣上刻着青云宗三个大字。",
        "used_hooks": [],
        "used_cards": [],
        "open_questions": []
    },
    "reviewer": {
        "consistency_issues": [],
        "style_issues": [{"type": "pace", "location": "开头", "description": "节奏略慢", "severity": "minor"}],
        "readability_score": 78,
        "hook_strength_score": 72,
        "actionable_suggestions": [{"type": "hook", "message": "建议在章节末尾增加悬念", "location": "结尾"}],
        "risk_level": "low"
    }
}


# ------------------------------------------------------------------
# 模型配置
# ------------------------------------------------------------------

def _load_llm_config() -> dict:
    """从环境变量 LLM_CONFIG 读取 per-agent 模型配置。"""
    raw = os.environ.get("LLM_CONFIG", "")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            import warnings
            warnings.warn(
                f"LLM_CONFIG 环境变量包含无效 JSON，使用默认配置。"
                f"当前值: {raw[:100]!r}",
                UserWarning
            )
    # 默认：全用 OpenAI GPT-4o
    return {
        "planner": "openai/gpt-4o",
        "writer": "openai/gpt-4o",
        "reviewer": "openai/gpt-4o",
        "committer": "openai/gpt-4o",
    }


def _get_api_key(model_name: str) -> str | None:
    """根据模型前缀从环境变量取对应 API key。"""
    prefix = model_name.split("/")[0].lower()
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "azure": "AZURE_API_KEY",
        "ollama": None,  # 本地 ollama 不需要 key
    }
    env_var = key_map.get(prefix)
    if env_var:
        return os.environ.get(env_var)
    return None


# ------------------------------------------------------------------
# LLM Client
# ------------------------------------------------------------------

class LLMClient:
    """
    统一 LLM 接口，底层用 LiteLLM。
    generate() 会根据 agent_type 选择对应模型。
    """

    DEFAULT_MODEL = "openai/gpt-4o"

    def __init__(self, model: str | None = None):
        self.config = _load_llm_config()
        self._default_model = model or self.DEFAULT_MODEL

    def generate(
        self,
        system: str,
        prompt: str,
        max_tokens: int = 4096,
        agent_type: str = ""
    ) -> str:
        """
        生成文本。

        Args:
            system:     系统提示词
            prompt:     用户输入
            max_tokens: 最大 token 数
            agent_type: Agent 类型（planner/writer/reviewer/committer）
                        决定用哪个模型

        Returns:
            生成的文本内容
        """
        if _mock_state["enabled"]:
            response_data = _mock_state["responses"].get(
                agent_type,
                _mock_state["responses"].get("reviewer", {})
            )
            return json.dumps(response_data)

        model = self.config.get(agent_type, self._default_model)
        api_key = _get_api_key(model)

        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            api_key=api_key,
        )

        return response.choices[0].message.content


# 兼容性别名
ClaudeClient = LLMClient


def set_mock_responses(responses: dict):
    _mock_state["enabled"] = True
    _mock_state["responses"] = responses


def reset_mock():
    _mock_state["enabled"] = False
    _mock_state["responses"] = {}


def load_prompt(name: str) -> str:
    # 优先读本地 templates/，fallback 到 services/api/app/templates/
    local_dir = Path(__file__).parent / "templates"
    path = local_dir / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    # 兼容旧路径
    api_dir = Path(__file__).parent.parent.parent / "services" / "api" / "app" / "templates"
    path = api_dir / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
