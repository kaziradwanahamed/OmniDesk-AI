"""Deterministic fakes for the OpenAI SDK (no network, no real keys)."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import openai


def fake_completion(
    content: str = "Hello from OpenAI.",
    model: str = "gpt-test",
    prompt: int = 12,
    completion: int = 8,
    total: int = 20,
    cid: str = "chatcmpl_test",
):
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(
        prompt_tokens=prompt, completion_tokens=completion, total_tokens=total
    )
    return SimpleNamespace(id=cid, model=model, choices=[choice], usage=usage)


class FakeOpenAI:
    """Mimics the subset of AsyncOpenAI the adapter uses."""

    def __init__(
        self,
        *,
        completion=None,
        create_error: Exception | None = None,
        models: list[str] | None = None,
        models_error: Exception | None = None,
    ) -> None:
        self._completion = completion
        self._create_error = create_error
        self._models = models or []
        self._models_error = models_error
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )
        self.models = SimpleNamespace(list=self._list)

    async def _create(self, **kwargs):
        if self._create_error is not None:
            raise self._create_error
        return self._completion

    async def _list(self):
        if self._models_error is not None:
            raise self._models_error
        return SimpleNamespace(data=[SimpleNamespace(id=i) for i in self._models])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def patch_client(monkeypatch, client: FakeOpenAI) -> None:
    monkeypatch.setattr(
        "app.adapters.openai_adapter._client", lambda api_key: client
    )


def _response(status: int) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "http://test"))


def auth_error() -> openai.AuthenticationError:
    return openai.AuthenticationError("invalid key", response=_response(401), body=None)


def rate_limit_error(code: str | None = None) -> openai.RateLimitError:
    body = {"code": code} if code else None
    return openai.RateLimitError("rate limited", response=_response(429), body=body)


def bad_request_context() -> openai.BadRequestError:
    return openai.BadRequestError(
        "maximum context length exceeded", response=_response(400), body=None
    )


def timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(httpx.Request("POST", "http://test"))


def connection_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(
        message="network down", request=httpx.Request("POST", "http://test")
    )


def server_error() -> openai.InternalServerError:
    return openai.InternalServerError("boom", response=_response(500), body=None)


# ============================ Anthropic fakes ============================

import anthropic  # noqa: E402


def fake_anthropic_message(
    text: str = "Hi from Claude.",
    model: str = "claude-test",
    input_tokens: int = 9,
    output_tokens: int = 6,
    mid: str = "msg_test",
):
    block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(
        id=mid, model=model, content=[block], usage=usage, stop_reason="end_turn"
    )


class FakeAnthropic:
    def __init__(
        self, *, message=None, create_error=None, models=None, models_error=None
    ):
        self._message = message
        self._create_error = create_error
        self._models = models or []
        self._models_error = models_error
        self.messages = SimpleNamespace(create=self._create)
        self.models = SimpleNamespace(list=self._list)

    async def _create(self, **kwargs):
        if self._create_error is not None:
            raise self._create_error
        return self._message

    async def _list(self):
        if self._models_error is not None:
            raise self._models_error
        return SimpleNamespace(data=[SimpleNamespace(id=i) for i in self._models])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def patch_anthropic(monkeypatch, client: FakeAnthropic) -> None:
    monkeypatch.setattr(
        "app.adapters.anthropic_adapter._client", lambda api_key: client
    )


def anthropic_auth_error():
    return anthropic.AuthenticationError("invalid", response=_response(401), body=None)


def anthropic_rate_error():
    return anthropic.RateLimitError("rate limited", response=_response(429), body=None)


def anthropic_bad_request(message: str = "bad request"):
    return anthropic.BadRequestError(message, response=_response(400), body=None)


def anthropic_overloaded():
    return anthropic.InternalServerError("overloaded", response=_response(529), body=None)


def anthropic_timeout():
    return anthropic.APITimeoutError(httpx.Request("POST", "http://test"))


# ============================= Gemini fakes =============================

from google.genai import errors as genai_errors  # noqa: E402


def fake_gemini_response(
    text: str = "Hi from Gemini.",
    prompt: int = 8,
    candidates: int = 4,
    total: int = 12,
    rid: str = "resp_test",
):
    usage = SimpleNamespace(
        prompt_token_count=prompt,
        candidates_token_count=candidates,
        total_token_count=total,
    )
    return SimpleNamespace(text=text, usage_metadata=usage, response_id=rid)


class _FakeGeminiModels:
    def __init__(self, response=None, error=None, models=None, models_error=None):
        self._response = response
        self._error = error
        self._models = models or []
        self._models_error = models_error

    async def generate_content(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._response

    async def list(self):
        if self._models_error is not None:
            raise self._models_error

        async def _gen():
            for name in self._models:
                yield SimpleNamespace(name=name, supported_actions=["generateContent"])

        return _gen()


class FakeGemini:
    def __init__(self, *, response=None, error=None, models=None, models_error=None):
        self.aio = SimpleNamespace(
            models=_FakeGeminiModels(response, error, models, models_error)
        )


def patch_gemini(monkeypatch, client: FakeGemini) -> None:
    monkeypatch.setattr("app.adapters.gemini_adapter._client", lambda api_key: client)


def gemini_error(code: int, message: str, status: str = ""):
    cls = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return cls(code, {"error": {"message": message, "status": status}})
