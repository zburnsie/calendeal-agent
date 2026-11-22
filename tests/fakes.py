"""A scripted chat model so agent tests run offline with no API key."""
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedModel(BaseChatModel):
    """Returns the next AIMessage from `script` on each call. bind_tools is a no-op."""

    script: list
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        msg = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])


def tool_call(name: str, args: dict, call_id: str = "c1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


class StubStructured:
    """Stands in for model.with_structured_output(schema): returns a fixed object."""

    def __init__(self, result):
        self.result = result

    def with_structured_output(self, schema, **kw):
        return self

    def invoke(self, prompt):
        return self.result
