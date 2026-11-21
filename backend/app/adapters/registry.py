"""Adapter registry. Phase 4-5 register openai/gemini/anthropic here."""

from __future__ import annotations

from app.adapters.base import BaseProviderAdapter, ProviderError
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.stub import StubEchoAdapter

_ADAPTERS: dict[str, BaseProviderAdapter] = {
    "stub": StubEchoAdapter(),
    "openai": OpenAIAdapter(),
}

# Providers that can be configured in Provider Settings (Phase 5 adds the rest).
SUPPORTED_PROVIDERS: tuple[str, ...] = ("openai",)


def get_adapter(provider: str) -> BaseProviderAdapter:
    adapter = _ADAPTERS.get(provider)
    if adapter is None:
        raise ProviderError(
            "MODEL_UNAVAILABLE",
            f"No adapter configured for provider '{provider}'.",
        )
    return adapter
