"""Anthropic adapter: message conversion, normalization, error mapping (mocked)."""

from __future__ import annotations

import pytest

from app.adapters.anthropic_adapter import AnthropicAdapter, _build_kwargs, _to_messages
from app.adapters.base import CanonicalMessage, ProviderError, ProviderRequest
from tests.fakes import (
    FakeAnthropic,
    anthropic_auth_error,
    anthropic_bad_request,
    anthropic_overloaded,
    anthropic_rate_error,
    anthropic_timeout,
    fake_anthropic_message,
    patch_anthropic,
)


def _req(messages=None, system="Be concise.") -> ProviderRequest:
    return ProviderRequest(
        model_id="claude-test",
        system_prompt=system,
        messages=messages or [CanonicalMessage(role="user", content="Hi")],
    )


def test_to_messages_merges_and_starts_with_user() -> None:
    req = _req(
        messages=[
            CanonicalMessage(role="assistant", content="prior from another model"),
            CanonicalMessage(role="user", content="u1"),
            CanonicalMessage(role="user", content="u2"),
            CanonicalMessage(role="assistant", content="a1"),
        ]
    )
    assert _to_messages(req) == [
        {"role": "user", "content": "u1\n\nu2"},
        {"role": "assistant", "content": "a1"},
    ]


def test_system_is_top_level_not_in_messages() -> None:
    kwargs = _build_kwargs(_req(system="SYSTEM PROMPT"))
    assert kwargs["system"] == "SYSTEM PROMPT"
    assert "max_tokens" in kwargs
    assert all(m["content"] != "SYSTEM PROMPT" for m in kwargs["messages"])


def test_no_system_key_when_empty() -> None:
    assert "system" not in _build_kwargs(_req(system=""))


async def test_generate_normalizes(monkeypatch) -> None:
    patch_anthropic(
        monkeypatch,
        FakeAnthropic(
            message=fake_anthropic_message(
                text="Hello!", model="claude-test", input_tokens=9, output_tokens=6, mid="msg_1"
            )
        ),
    )
    resp = await AnthropicAdapter().generate(_req(), "sk-ant-key")
    assert resp.provider == "anthropic"
    assert resp.model_id == "claude-test"
    assert resp.content == "Hello!"
    assert resp.usage.input_tokens == 9
    assert resp.usage.output_tokens == 6
    assert resp.usage.total_tokens == 15
    assert resp.provider_request_id == "msg_1"


async def test_generate_requires_key() -> None:
    with pytest.raises(ProviderError) as exc:
        await AnthropicAdapter().generate(_req(), None)
    assert exc.value.category == "AUTH_INVALID_KEY"


@pytest.mark.parametrize(
    "make_error,category",
    [
        (anthropic_auth_error, "AUTH_INVALID_KEY"),
        (anthropic_rate_error, "RATE_LIMITED"),
        (lambda: anthropic_bad_request("Your credit balance is too low"), "QUOTA_EXCEEDED"),
        (lambda: anthropic_bad_request("prompt is too long for the context window"), "CONTEXT_TOO_LARGE"),
        (anthropic_timeout, "TIMEOUT"),
        (anthropic_overloaded, "MODEL_UNAVAILABLE"),
    ],
)
async def test_error_mapping(monkeypatch, make_error, category) -> None:
    patch_anthropic(monkeypatch, FakeAnthropic(create_error=make_error()))
    with pytest.raises(ProviderError) as exc:
        await AnthropicAdapter().generate(_req(), "sk-ant-key")
    assert exc.value.category == category


async def test_list_models_sorted(monkeypatch) -> None:
    patch_anthropic(monkeypatch, FakeAnthropic(models=["claude-b", "claude-a"]))
    assert await AnthropicAdapter().list_models("sk-ant-key") == ["claude-a", "claude-b"]
