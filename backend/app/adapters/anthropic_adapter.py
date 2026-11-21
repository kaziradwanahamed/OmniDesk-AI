"""Anthropic Claude adapter (official `anthropic` SDK, Messages API).

Verified against anthropic 2.12.0: AsyncAnthropic(api_key, timeout, max_retries),
messages.create(model, system, messages, max_tokens, stream), response.content[*]
.text, response.usage.{input,output}_tokens, response.id, client.models.list()
.data[*].id. System goes in the top-level `system` param; messages strictly
alternate user/assistant (adjacent same-role turns are merged, and the sequence
is forced to start with a user turn). No model IDs are hardcoded.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import anthropic
from anthropic import AsyncAnthropic

from app.adapters.base import (
    BaseProviderAdapter,
    NormalizedUsage,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
)

_TIMEOUT_SECONDS = 60.0
_DEFAULT_MAX_TOKENS = 2048


def _client(api_key: str) -> AsyncAnthropic:
    return AsyncAnthropic(
        api_key=api_key, timeout=_TIMEOUT_SECONDS, max_retries=0
    )


def _to_messages(req: ProviderRequest) -> list[dict]:
    """Canonical -> Anthropic messages: map roles, merge adjacent same-role turns,
    and drop any leading assistant turns so the sequence starts with `user`."""
    merged: list[dict] = []
    for m in req.messages:
        role = "assistant" if m.role == "assistant" else "user"
        if merged and merged[-1]["role"] == role:
            merged[-1]["content"] += "\n\n" + m.content
        else:
            merged.append({"role": role, "content": m.content})
    while merged and merged[0]["role"] == "assistant":
        merged.pop(0)
    return merged


def _build_kwargs(req: ProviderRequest) -> dict:
    kwargs: dict = {
        "model": req.model_id,
        "messages": _to_messages(req),
        "max_tokens": req.max_output_tokens or _DEFAULT_MAX_TOKENS,
    }
    if req.system_prompt:
        kwargs["system"] = req.system_prompt
    return kwargs


def _text_from_content(content) -> str:
    parts = []
    for block in content or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def _usage(usage) -> NormalizedUsage:
    if usage is None:
        return NormalizedUsage()
    inp = getattr(usage, "input_tokens", None)
    out = getattr(usage, "output_tokens", None)
    total = None if inp is None and out is None else (inp or 0) + (out or 0)
    return NormalizedUsage(input_tokens=inp, output_tokens=out, total_tokens=total)


def _retry_after(exc: Exception) -> int | None:
    try:
        response = getattr(exc, "response", None)
        if response is not None:
            value = response.headers.get("retry-after")
            if value:
                return int(float(value))
    except Exception:  # noqa: BLE001
        return None
    return None


def _normalize_error(exc: Exception) -> ProviderError:
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return ProviderError("AUTH_INVALID_KEY", "Invalid or revoked Anthropic API key.")
    if isinstance(exc, anthropic.RateLimitError):
        return ProviderError(
            "RATE_LIMITED",
            "Anthropic rate limit reached. Try again shortly.",
            retry_after_seconds=_retry_after(exc),
        )
    if isinstance(exc, anthropic.APITimeoutError):
        return ProviderError("TIMEOUT", "The Anthropic request timed out.")
    if isinstance(exc, anthropic.BadRequestError):
        message = str(getattr(exc, "message", "") or exc).lower()
        if "credit" in message or "billing" in message or "quota" in message:
            return ProviderError(
                "QUOTA_EXCEEDED", "Anthropic credit/quota exhausted — check billing."
            )
        if "too long" in message or "context" in message or "max_tokens" in message:
            return ProviderError(
                "CONTEXT_TOO_LARGE", "The conversation exceeds Claude's context window."
            )
        return ProviderError("MODEL_UNAVAILABLE", "Anthropic rejected the request.")
    if isinstance(exc, anthropic.NotFoundError):
        return ProviderError("MODEL_UNAVAILABLE", "The requested Claude model was not found.")
    if isinstance(exc, anthropic.APIConnectionError):
        return ProviderError("MODEL_UNAVAILABLE", "Could not reach Anthropic (network error).")
    if isinstance(exc, (anthropic.InternalServerError, anthropic.APIStatusError)):
        # Includes 529 overloaded_error.
        return ProviderError("MODEL_UNAVAILABLE", "Anthropic is overloaded or unavailable.")
    return ProviderError("MODEL_UNAVAILABLE", "Unexpected provider error.")


class AnthropicAdapter(BaseProviderAdapter):
    provider_name = "anthropic"

    async def generate(
        self, req: ProviderRequest, api_key: str | None
    ) -> ProviderResponse:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No Anthropic API key configured.")
        try:
            async with _client(api_key) as client:
                resp = await client.messages.create(**_build_kwargs(req))
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc

        return ProviderResponse(
            provider="anthropic",
            model_id=getattr(resp, "model", None) or req.model_id,
            content=_text_from_content(resp.content),
            usage=_usage(resp.usage),
            provider_request_id=getattr(resp, "id", None),
            finish_reason=getattr(resp, "stop_reason", None),
        )

    async def stream(
        self, req: ProviderRequest, api_key: str | None
    ) -> AsyncIterator[StreamChunk]:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No Anthropic API key configured.")
        try:
            async with _client(api_key) as client:
                stream = await client.messages.create(stream=True, **_build_kwargs(req))
                request_id: str | None = None
                input_tokens: int | None = None
                output_tokens: int | None = None
                finish_reason: str | None = None
                async for event in stream:
                    etype = getattr(event, "type", None)
                    if etype == "message_start":
                        request_id = getattr(event.message, "id", None)
                        input_tokens = getattr(event.message.usage, "input_tokens", None)
                    elif etype == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        if getattr(delta, "type", None) == "text_delta":
                            yield StreamChunk(delta_text=delta.text)
                    elif etype == "message_delta":
                        output_tokens = getattr(
                            getattr(event, "usage", None), "output_tokens", output_tokens
                        )
                        finish_reason = getattr(
                            getattr(event, "delta", None), "stop_reason", finish_reason
                        )
                total = (
                    None
                    if input_tokens is None and output_tokens is None
                    else (input_tokens or 0) + (output_tokens or 0)
                )
                yield StreamChunk(
                    is_final=True,
                    usage=NormalizedUsage(input_tokens, output_tokens, total),
                    provider_request_id=request_id,
                    finish_reason=finish_reason,
                )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc

    async def list_models(self, api_key: str | None) -> list[str]:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No Anthropic API key configured.")
        try:
            async with _client(api_key) as client:
                result = await client.models.list()
                return sorted(m.id for m in result.data)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc
