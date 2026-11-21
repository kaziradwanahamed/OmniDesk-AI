"""OpenAI adapter normalization + error mapping (mocked SDK, no network)."""

from __future__ import annotations

import pytest

from app.adapters.base import CanonicalMessage, ProviderError, ProviderRequest
from app.adapters.openai_adapter import OpenAIAdapter
from tests.fakes import (
    FakeOpenAI,
    auth_error,
    bad_request_context,
    connection_error,
    fake_completion,
    patch_client,
    rate_limit_error,
    server_error,
    timeout_error,
)


def _req() -> ProviderRequest:
    return ProviderRequest(
        model_id="gpt-test",
        system_prompt="Be concise.",
        messages=[CanonicalMessage(role="user", content="Hi")],
    )


async def test_generate_normalizes_response(monkeypatch) -> None:
    patch_client(
        monkeypatch,
        FakeOpenAI(
            completion=fake_completion(
                content="Hello!", model="gpt-test", prompt=10, completion=5, total=15, cid="req_1"
            )
        ),
    )
    resp = await OpenAIAdapter().generate(_req(), "sk-key")
    assert resp.provider == "openai"
    assert resp.model_id == "gpt-test"
    assert resp.content == "Hello!"
    assert resp.usage.input_tokens == 10
    assert resp.usage.output_tokens == 5
    assert resp.usage.total_tokens == 15
    assert resp.provider_request_id == "req_1"


async def test_generate_requires_api_key() -> None:
    with pytest.raises(ProviderError) as exc:
        await OpenAIAdapter().generate(_req(), None)
    assert exc.value.category == "AUTH_INVALID_KEY"


async def test_list_models_returns_sorted(monkeypatch) -> None:
    patch_client(monkeypatch, FakeOpenAI(models=["gpt-b", "gpt-a"]))
    models = await OpenAIAdapter().list_models("sk-key")
    assert models == ["gpt-a", "gpt-b"]


@pytest.mark.parametrize(
    "make_error,category",
    [
        (auth_error, "AUTH_INVALID_KEY"),
        (lambda: rate_limit_error(), "RATE_LIMITED"),
        (lambda: rate_limit_error("insufficient_quota"), "QUOTA_EXCEEDED"),
        (bad_request_context, "CONTEXT_TOO_LARGE"),
        (timeout_error, "TIMEOUT"),
        (connection_error, "MODEL_UNAVAILABLE"),
        (server_error, "MODEL_UNAVAILABLE"),
    ],
)
async def test_generate_error_mapping(monkeypatch, make_error, category) -> None:
    patch_client(monkeypatch, FakeOpenAI(create_error=make_error()))
    with pytest.raises(ProviderError) as exc:
        await OpenAIAdapter().generate(_req(), "sk-key")
    assert exc.value.category == category
