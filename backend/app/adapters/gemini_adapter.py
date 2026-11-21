"""Google Gemini adapter (official `google-genai` SDK — NOT google-generativeai).

Verified against google-genai 3.6.1: genai.Client(api_key, http_options).aio.models
.{generate_content,generate_content_stream,list}, types.GenerateContentConfig(
system_instruction, max_output_tokens), response.text, response.usage_metadata
.{prompt_token_count,candidates_token_count,total_token_count}, response.response_id,
errors.APIError(.code). Canonical roles map assistant->"model", user->"user";
system goes via system_instruction; adjacent same-role turns are merged and the
sequence is forced to start with a user turn. No model IDs are hardcoded.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.adapters.base import (
    BaseProviderAdapter,
    NormalizedUsage,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
)

_TIMEOUT_MS = 60_000


def _client(api_key: str) -> genai.Client:
    return genai.Client(
        api_key=api_key, http_options=types.HttpOptions(timeout=_TIMEOUT_MS)
    )


def _merge_contents(req: ProviderRequest) -> list[dict]:
    """Canonical -> merged (role, text) with assistant->model and leading model
    turns dropped so the sequence starts with `user`."""
    merged: list[dict] = []
    for m in req.messages:
        role = "model" if m.role == "assistant" else "user"
        if merged and merged[-1]["role"] == role:
            merged[-1]["text"] += "\n\n" + m.content
        else:
            merged.append({"role": role, "text": m.content})
    while merged and merged[0]["role"] == "model":
        merged.pop(0)
    return merged


def _to_contents(req: ProviderRequest) -> list[types.Content]:
    return [
        types.Content(role=item["role"], parts=[types.Part(text=item["text"])])
        for item in _merge_contents(req)
    ]


def _config(req: ProviderRequest) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=req.system_prompt or None,
        max_output_tokens=req.max_output_tokens,
    )


def _usage(meta) -> NormalizedUsage:
    if meta is None:
        return NormalizedUsage()
    return NormalizedUsage(
        input_tokens=getattr(meta, "prompt_token_count", None),
        output_tokens=getattr(meta, "candidates_token_count", None),
        total_tokens=getattr(meta, "total_token_count", None),
    )


def _normalize_error(exc: Exception) -> ProviderError:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderError("TIMEOUT", "The Gemini request timed out.")
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        message = (getattr(exc, "message", None) or str(exc) or "").lower()
        if code in (401, 403) or "api key not valid" in message or "api_key" in message:
            return ProviderError("AUTH_INVALID_KEY", "Invalid or missing Gemini API key.")
        if code == 429:
            if "quota" in message or "billing" in message:
                return ProviderError("QUOTA_EXCEEDED", "Gemini quota exceeded.")
            return ProviderError("RATE_LIMITED", "Gemini rate limit reached.")
        if code == 400:
            if "token" in message and ("exceed" in message or "maximum" in message):
                return ProviderError(
                    "CONTEXT_TOO_LARGE", "The request exceeds the Gemini context window."
                )
            return ProviderError("MODEL_UNAVAILABLE", "Gemini rejected the request.")
        if code == 404:
            return ProviderError("MODEL_UNAVAILABLE", "The requested Gemini model was not found.")
        if code is not None and code >= 500:
            return ProviderError("MODEL_UNAVAILABLE", "Gemini is temporarily unavailable.")
        return ProviderError("MODEL_UNAVAILABLE", "Unexpected Gemini error.")
    if isinstance(exc, (httpx.HTTPError, ConnectionError, OSError)):
        return ProviderError("MODEL_UNAVAILABLE", "Could not reach Gemini (network error).")
    return ProviderError("MODEL_UNAVAILABLE", "Unexpected Gemini error.")


class GeminiAdapter(BaseProviderAdapter):
    provider_name = "gemini"

    async def generate(
        self, req: ProviderRequest, api_key: str | None
    ) -> ProviderResponse:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No Gemini API key configured.")
        try:
            client = _client(api_key)
            resp = await client.aio.models.generate_content(
                model=req.model_id, contents=_to_contents(req), config=_config(req)
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc

        return ProviderResponse(
            provider="gemini",
            model_id=req.model_id,
            content=getattr(resp, "text", None) or "",
            usage=_usage(getattr(resp, "usage_metadata", None)),
            provider_request_id=getattr(resp, "response_id", None),
        )

    async def stream(
        self, req: ProviderRequest, api_key: str | None
    ) -> AsyncIterator[StreamChunk]:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No Gemini API key configured.")
        try:
            client = _client(api_key)
            gen = client.aio.models.generate_content_stream(
                model=req.model_id, contents=_to_contents(req), config=_config(req)
            )
            if inspect.isawaitable(gen):
                gen = await gen
            usage: NormalizedUsage | None = None
            request_id: str | None = None
            async for chunk in gen:
                text = getattr(chunk, "text", None)
                if text:
                    yield StreamChunk(delta_text=text)
                meta = getattr(chunk, "usage_metadata", None)
                if meta is not None:
                    usage = _usage(meta)
                request_id = request_id or getattr(chunk, "response_id", None)
            yield StreamChunk(
                is_final=True, usage=usage, provider_request_id=request_id
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc

    async def list_models(self, api_key: str | None) -> list[str]:
        if not api_key:
            raise ProviderError("AUTH_INVALID_KEY", "No Gemini API key configured.")
        try:
            client = _client(api_key)
            pager = client.aio.models.list()
            if inspect.isawaitable(pager):
                pager = await pager
            out: list[str] = []
            async for model in pager:
                name = getattr(model, "name", None) or ""
                if name.startswith("models/"):
                    name = name[len("models/") :]
                actions = getattr(model, "supported_actions", None)
                if actions and "generateContent" not in actions:
                    continue
                if name:
                    out.append(name)
            return sorted(set(out))
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _normalize_error(exc) from exc
