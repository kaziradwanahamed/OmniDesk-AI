"""OpenAI adapter (official `openai` SDK, Chat Completions API).

Verified against openai 3.57.0: AsyncOpenAI(api_key, timeout, max_retries),
client.chat.completions.create(model, messages, max_completion_tokens, stream,
stream_options), usage.{prompt,completion,total}_tokens, chunk.choices[0].delta
.content, client.models.list().data[*].id. No model IDs are hardcoded — the
selectable list comes from client.models.list() (the user's verified models).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import openai
from openai import AsyncOpenAI

from app.adapters.base import (
    BaseProviderAdapter,
    NormalizedUsage,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
)

_TIMEOUT_SECONDS = 60.0


def _client(api_key: str) -> AsyncOpenAI:
    # max_retries=0 so OmniDesk controls retry/fallback semantics deterministically.
    return AsyncOpenAI(api_key=api_key, timeout=_TIMEOUT_SECONDS, max_retries=0)


def _to_openai_messages(req: ProviderRequest) -> list[dict]:
    messages: list[dict] = []
    if req.system_prompt:
        messages.append({"role": "system", "content": req.system_prompt})
    for m in req.messages:
        messages.append({"role": m.role, "content": m.content})
    return messages


def _normalize_usage(usage) -> NormalizedUsage:
    if usage is None:
        return NormalizedUsage()
    return NormalizedUsage(
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )


def _is_insufficient_quota(exc: Exception) -> bool:
    for attr in ("code", "type"):
        if getattr(exc, attr, None) == "insufficient_quota":
            return True
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        if body.get("code") == "insufficient_quota":
            return True
        err = body.get("error")
        if isinstance(err, dict) and err.get("code") == "insufficient_quota":
            return True
    return False


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
    if isinstance(exc, openai.AuthenticationError):
        return ProviderError("AUTH_INVALID_KEY", "Invalid or revoked OpenAI API key.")
    if isinstance(exc, openai.PermissionDeniedError):
        return ProviderError(
            "AUTH_INVALID_KEY", "This OpenAI key lacks access to the requested model."
        )
    if isinstance(exc, openai.RateLimitError):
        if _is_insufficient_quota(exc):
            return ProviderError(
                "QUOTA_EXCEEDED",
                "OpenAI quota exceeded — check your plan and billing.",
            )
        return ProviderError(
            "RATE_LIMITED",
            "OpenAI rate limit reached. Try again shortly.",
            retry_after_seconds=_retry_after(exc),
        )
    if isinstance(exc, openai.APITimeoutError):
        return ProviderError("TIMEOUT", "The OpenAI request timed out.")
    if isinstance(exc, openai.BadRequestError):
        message = str(getattr(exc, "message", "") or exc)
        if (
            getattr(exc, "code", None) == "context_length_exceeded"
            or "context length" in message.lower()
            or "maximum context" in message.lower()
        ):
            return ProviderError(
                "CONTEXT_TOO_LARGE",
                "The conversation exceeds the model's context window.",
            )
        return ProviderError("MODEL_UNAVAILABLE", "OpenAI rejected the request.")
    if isinstance(exc, openai.NotFoundError):
        return ProviderError("MODEL_UNAVAILABLE", "The requested model was not found.")
    if isinstance(exc, openai.APIConnectionError):
        return ProviderError(
            "MODEL_UNAVAILABLE", "Could not reach OpenAI (network error)."
        )
    if isinstance(exc, (openai.InternalServerError, openai.APIStatusError)):
        return ProviderError("MODEL_UNAVAILABLE", "OpenAI is temporarily unavailable.")
    return ProviderError("MODEL_UNAVAILABLE", "Unexpected provider error.")


class OpenAIAdapter(BaseProviderAdapter):
    provider_name = "openai"

    async def generate(
        self, req: ProviderRequest, api_key: str | None
    ) -> ProviderResponse:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No OpenAI API key configured.")
        try:
            async with _client(api_key) as client:
                resp = await client.chat.completions.create(
                    model=req.model_id,
                    messages=_to_openai_messages(req),
                    max_completion_tokens=req.max_output_tokens,
                )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc

        choice = resp.choices[0] if resp.choices else None
        content = (choice.message.content if choice and choice.message else "") or ""
        return ProviderResponse(
            provider="openai",
            model_id=resp.model or req.model_id,
            content=content,
            usage=_normalize_usage(resp.usage),
            provider_request_id=resp.id,
            finish_reason=choice.finish_reason if choice else None,
        )

    async def stream(
        self, req: ProviderRequest, api_key: str | None
    ) -> AsyncIterator[StreamChunk]:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No OpenAI API key configured.")
        try:
            async with _client(api_key) as client:
                stream = await client.chat.completions.create(
                    model=req.model_id,
                    messages=_to_openai_messages(req),
                    max_completion_tokens=req.max_output_tokens,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                request_id: str | None = None
                usage: NormalizedUsage | None = None
                finish_reason: str | None = None
                async for chunk in stream:
                    request_id = request_id or chunk.id
                    if chunk.usage is not None:
                        usage = _normalize_usage(chunk.usage)
                    if chunk.choices:
                        ch = chunk.choices[0]
                        if ch.finish_reason:
                            finish_reason = ch.finish_reason
                        delta = ch.delta.content if ch.delta else None
                        if delta:
                            yield StreamChunk(delta_text=delta)
                yield StreamChunk(
                    is_final=True,
                    usage=usage,
                    provider_request_id=request_id,
                    finish_reason=finish_reason,
                )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc

    async def list_models(self, api_key: str | None) -> list[str]:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No OpenAI API key configured.")
        try:
            async with _client(api_key) as client:
                result = await client.models.list()
                return sorted(model.id for model in result.data)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc
