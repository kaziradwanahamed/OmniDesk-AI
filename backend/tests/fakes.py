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
