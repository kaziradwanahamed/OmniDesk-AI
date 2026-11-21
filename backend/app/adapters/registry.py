"""Adapter registry. Phase 4-5 register openai/gemini/anthropic here."""

from __future__ import annotations

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.base import BaseProviderAdapter, ProviderError
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.stub import StubEchoAdapter

_ADAPTERS: dict[str, BaseProviderAdapter] = {
    "stub": StubEchoAdapter(),
    "openai": OpenAIAdapter(),
    "gemini": GeminiAdapter(),
    "anthropic": AnthropicAdapter(),
}

# Providers that can be configured in Provider Settings.
SUPPORTED_PROVIDERS: tuple[str, ...] = ("openai", "gemini", "anthropic")


def get_adapter(provider: str) -> BaseProviderAdapter:
    adapter = _ADAPTERS.get(provider)
    if adapter is None:
        raise ProviderError(
            "MODEL_UNAVAILABLE",
            f"No adapter configured for provider '{provider}'.",
        )
    return adapter
