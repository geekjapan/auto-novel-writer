from __future__ import annotations

import os

from novel_writer.llm.base import BaseLLMClient
from novel_writer.llm.mock import MockLLMClient
from novel_writer.llm.openai_client import OpenAIClient


def resolve_openai_provider_settings(
    provider: str,
    model: str = "gpt-4.1-mini",
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, str]:
    normalized = provider.lower()
    provider_configs = {
        "openai": {
            "provider_label": "OpenAI",
            "base_url_env": "OPENAI_BASE_URL",
            "api_key_env": "OPENAI_API_KEY",
            "default_base_url": None,
            "default_api_key": None,
            "requires_base_url": False,
            "response_format_type": "json_object",
        },
        "openai-compatible": {
            "provider_label": "OpenAI-compatible",
            "base_url_env": "OPENAI_COMPATIBLE_BASE_URL",
            "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
            "default_base_url": None,
            "default_api_key": "openai-compatible-local",
            "requires_base_url": True,
            "response_format_type": "text",
        },
        "lmstudio": {
            "provider_label": "LM Studio",
            "base_url_env": "LMSTUDIO_BASE_URL",
            "api_key_env": "LMSTUDIO_API_KEY",
            "default_base_url": "http://127.0.0.1:1234/v1",
            "default_api_key": "lm-studio",
            "requires_base_url": False,
            "response_format_type": "text",
        },
        "ollama": {
            "provider_label": "Ollama",
            "base_url_env": "OLLAMA_BASE_URL",
            "api_key_env": "OLLAMA_API_KEY",
            "default_base_url": "http://127.0.0.1:11434/v1",
            "default_api_key": "ollama",
            "requires_base_url": False,
            "response_format_type": "text",
        },
    }
    config = provider_configs.get(normalized)
    if config is None:
        raise ValueError(f"Unsupported provider: {provider}")

    resolved_base_url = base_url or os.getenv(config["base_url_env"]) or config["default_base_url"]
    resolved_api_key = api_key or os.getenv(config["api_key_env"]) or config["default_api_key"]
    if config["requires_base_url"] and not resolved_base_url:
        raise RuntimeError(
            f"{config['provider_label']} provider requires --base-url or {config['base_url_env']}."
        )
    if not resolved_api_key:
        raise RuntimeError(
            f"{config['provider_label']} provider requires --api-key or {config['api_key_env']}."
        )
    settings = {
        "model": model,
        "api_key": resolved_api_key,
        "provider_label": config["provider_label"],
        "response_format_type": config["response_format_type"],
    }
    if resolved_base_url:
        settings["base_url"] = resolved_base_url
    return settings


def build_llm_client(
    provider: str,
    model: str = "gpt-4.1-mini",
    base_url: str | None = None,
    api_key: str | None = None,
) -> BaseLLMClient:
    normalized = provider.lower()
    if normalized == "mock":
        return MockLLMClient()
    if normalized in {"openai", "openai-compatible", "lmstudio", "ollama"}:
        return OpenAIClient(**resolve_openai_provider_settings(provider, model=model, base_url=base_url, api_key=api_key))
    raise ValueError(f"Unsupported provider: {provider}")

