from __future__ import annotations

from novel_writer.llm.base import BaseLLMClient
from novel_writer.llm.mock import MockLLMClient
from novel_writer.llm.openai_client import OpenAIClient


def build_llm_client(provider: str, model: str = "gpt-4.1-mini") -> BaseLLMClient:
    normalized = provider.lower()
    if normalized == "mock":
        return MockLLMClient()
    if normalized == "openai":
        return OpenAIClient(model=model)
    raise ValueError(f"Unsupported provider: {provider}")

