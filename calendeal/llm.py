"""One place to get the chat model, so every part of CalenDeal uses the same LLM.

Default: DeepSeek's cheap model (`deepseek-flash`), through LangChain's init_chat_model, the
same call the labs use. Switch with CALENDEAL_LLM in .env:

    CALENDEAL_LLM=deepseek:deepseek-flash        # default; needs DEEPSEEK_API_KEY
    CALENDEAL_LLM=anthropic:claude-haiku-4-5     # needs ANTHROPIC_API_KEY
    CALENDEAL_LLM=ollama:qwen2.5:7b              # local, free, no key (like the labs)

DeepSeek "thinking" mode is OFF by default. With it on, DeepSeek requires the model's
reasoning_content to be sent back on every later turn once tools are involved, or it returns 400.
Set CALENDEAL_DEEPSEEK_THINKING=1 to turn it back on for non-agent calls if you want.

If no key is set for the chosen provider, get_model() returns None and every caller falls back to
a no-LLM path (retrieval order, plain search results), so the app still runs for demos.
"""
from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

DEFAULT_LLM = "deepseek:deepseek-flash"
KEY_FOR = {"deepseek": "DEEPSEEK_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
MAX_RETRIES = 3

T = TypeVar("T", bound=BaseModel)


def model_name() -> str:
    return os.getenv("CALENDEAL_LLM", DEFAULT_LLM)


def available() -> bool:
    provider = model_name().split(":", 1)[0]
    key = KEY_FOR.get(provider)
    return key is None or bool(os.getenv(key))


def get_model(temperature: float = 0.3, thinking: bool | None = None):
    """A LangChain chat model, or None if the provider's API key isn't set."""
    if not available():
        return None
    from langchain.chat_models import init_chat_model

    name = model_name()
    kwargs = {"temperature": temperature}
    if name.startswith("deepseek:"):
        if thinking is None:
            thinking = os.getenv("CALENDEAL_DEEPSEEK_THINKING") == "1"
        kwargs["extra_body"] = {"thinking": {"type": "enabled" if thinking else "disabled"}}
    return init_chat_model(name, **kwargs)


def structured(schema: type[T], prompt: str, model=None, max_retries: int = MAX_RETRIES) -> T | None:
    """Ask for output matching a Pydantic schema, with a bounded retry (same idea as Lab 4, script 2).

    Returns None if there's no model or every attempt failed validation.
    """
    model = model or get_model()
    if model is None:
        return None
    llm = model.with_structured_output(schema)
    last_error = None
    for _ in range(max_retries):
        try:
            return llm.invoke(prompt)
        except Exception as e:  # Pydantic ValidationError or a provider-side parse error
            last_error = e
    print(f"[warn] structured output failed after {max_retries} tries: {last_error}")
    return None
