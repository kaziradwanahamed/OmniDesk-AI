"""Canonical dataclasses and the base provider-adapter interface.

Services speak only in these canonical types; each adapter translates to and from
its vendor SDK. Phase 3 ships a stub adapter + ``generate``; Phase 4 adds the
streaming interface and the real OpenAI/Gemini/Anthropic adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

ErrorCategory = Literal[
    "AUTH_INVALID_KEY",
    "RATE_LIMITED",
    "QUOTA_EXCEEDED",
    "BILLING_REQUIRED",
    "CONTEXT_TOO_LARGE",
    "MODEL_UNAVAILABLE",
    "TIMEOUT",
]


@dataclass(frozen=True)
class CanonicalMessage:
    role: Literal["user", "assistant"]
    content: str
    source_provider: str | None = None
    source_model_id: str | None = None


@dataclass(frozen=True)
class NormalizedUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ProviderRequest:
    model_id: str
    system_prompt: str
    messages: list[CanonicalMessage]
    max_output_tokens: int = 2048
    temperature: float | None = None


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    model_id: str
    content: str
    usage: NormalizedUsage = field(default_factory=NormalizedUsage)
    provider_request_id: str | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class StreamChunk:
    delta_text: str = ""
    is_final: bool = False
    usage: NormalizedUsage | None = None
    provider_request_id: str | None = None
    finish_reason: str | None = None


class ProviderError(Exception):
    """Normalized provider failure with a UI-facing category and message."""

    def __init__(
        self,
        category: ErrorCategory,
        user_message: str,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(user_message)
        self.category = category
        self.user_message = user_message
        self.retry_after_seconds = retry_after_seconds


class BaseProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def generate(
        self, req: ProviderRequest, api_key: str | None
    ) -> ProviderResponse:
        """Produce a single, non-streaming response."""
        raise NotImplementedError

    @abstractmethod
    def stream(
        self, req: ProviderRequest, api_key: str | None
    ) -> AsyncIterator[StreamChunk]:
        """Yield streaming chunks; the final chunk carries usage when available."""
        raise NotImplementedError

    @abstractmethod
    async def list_models(self, api_key: str | None) -> list[str]:
        """Return the model IDs available to this credential (verified, not invented)."""
        raise NotImplementedError
