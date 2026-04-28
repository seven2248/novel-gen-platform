"""
Agent 基类：封装通用 run 模式（client → context → generate → parse → validate）
各 agent 只需定义 build_context() 和 prompt 模板。
"""
import json
from abc import ABC, abstractmethod
from packages.agents.src.base import ClaudeClient
from packages.agents.src.schema_validator import validate_payload


class BaseAgent(ABC):
    """
    Agent 抽象基类，定义 run 流程。

    注意（与现有 agent 的行为差异）：
    - JSON 解析失败时 → get_fallback() → schema 验证
      现有 agent（planner/writer/reviewer）的 run_* 函数则是：
      JSON 解析失败时 fallback → schema 验证失败时 raise ValueError
      两种行为顺序不一致，迁移时需对齐。
    - get_fallback() 默认返回 {}，若子类未重写且 JSON 解析失败，
      空 dict 会触发 schema 验证异常，相当于 fallback 形同虚设。
      子类必须重写 get_fallback() 以提供有意义的兜底值。
    """

    DEFAULT_SYSTEM: str = ""  # 子类必须定义
    SCHEMA_NAME: str = ""     # 子类必须定义

    def __init__(self):
        self.client = ClaudeClient()

    def run(self, *args, **kwargs) -> dict:
        """通用流程：构建 context → 调用 LLM → 解析 JSON → schema 验证"""
        context = self.build_context(*args, **kwargs)
        system = self.get_system()
        prompt = self.build_prompt(context, *args, **kwargs)

        response = self.client.generate(
            system, prompt,
            max_tokens=self.get_max_tokens(),
            agent_type=self.agent_type()
        )
        result = self.parse_response(response)

        valid, err = validate_payload(result, self.SCHEMA_NAME)
        if not valid:
            raise ValueError(f"{self.__class__.__name__} output validation failed: {err}")

        return result

    def get_system(self) -> str:
        name = self.system_prompt_name()
        if not name:
            return self.DEFAULT_SYSTEM
        from packages.agents.src.base import load_prompt
        loaded = load_prompt(name)
        return loaded or self.DEFAULT_SYSTEM

    @abstractmethod
    def agent_type(self) -> str:
        """返回 agent 类型字符串（如 'planner', 'writer'）"""
        pass

    @abstractmethod
    def build_context(self, *args, **kwargs) -> dict:
        """构建上下文字典，供 build_prompt 使用"""
        pass

    @abstractmethod
    def build_prompt(self, context: dict, *args, **kwargs) -> str:
        """从 context 构建 user prompt 字符串"""
        pass

    def system_prompt_name(self) -> str:
        """返回 prompt 模板文件名（不含 .txt），被子类覆盖或直接赋值"""
        return ""

    def parse_response(self, response: str) -> dict:
        """解析 LLM 响应，失败时返回 fallback"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self.get_fallback(response)

    def get_fallback(self, response: str) -> dict:
        """子类可重写，提供 JSON 解析失败时的 fallback"""
        return {}

    def get_max_tokens(self) -> int:
        return 4096


def agent_run(agent_class: type, *args, **kwargs) -> dict:
    """便捷函数：实例化 agent 并调用 run"""
    return agent_class().run(*args, **kwargs)
