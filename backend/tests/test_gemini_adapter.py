"""Gemini adapter: content conversion, normalization, error mapping (mocked)."""

from __future__ import annotations

import pytest

from app.adapters.base import CanonicalMessage, ProviderError, ProviderRequest
from app.adapters.gemini_adapter import GeminiAdapter, _config, _merge_contents
from tests.fakes import FakeGemini, fake_gemini_response, gemini_error, patch_gemini


def _req(messages=None, system="Be concise.") -> ProviderRequest:
    return ProviderRequest(
        model_id="gemini-test",
        system_prompt=system,
        messages=messages or [CanonicalMessage(role="user", content="Hi")],
    )


def test_merge_contents_maps_roles_merges_starts_user() -> None:
    req = _req(
        messages=[
            CanonicalMessage(role="assistant", content="prior from another model"),
            CanonicalMessage(role="user", content="u1"),
            CanonicalMessage(role="user", content="u2"),
            CanonicalMessage(role="assistant", content="a1"),
        ]
    )
    assert _merge_contents(req) == [
        {"role": "user", "text": "u1\n\nu2"},
        {"role": "model", "text": "a1"},
    ]


def test_system_goes_in_config() -> None:
    assert _config(_req(system="SYS")).system_instruction == "SYS"


async def test_generate_normalizes(monkeypatch) -> None:
    patch_gemini(
        monkeypatch,
        FakeGemini(
            response=fake_gemini_response(
                text="Hello!", prompt=8, candidates=4, total=12, rid="resp_1"
            )
        ),
    )
    resp = await GeminiAdapter().generate(_req(), "AIza-key")
    assert resp.provider == "gemini"
    assert resp.model_id == "gemini-test"
    assert resp.content == "Hello!"
    assert resp.usage.input_tokens == 8
    assert resp.usage.output_tokens == 4
    assert resp.usage.total_tokens == 12
    assert resp.provider_request_id == "resp_1"


async def test_generate_requires_key() -> None:
    with pytest.raises(ProviderError) as exc:
        await GeminiAdapter().generate(_req(), None)
    assert exc.value.category == "AUTH_INVALID_KEY"


@pytest.mark.parametrize(
    "err,category",
    [
        (gemini_error(400, "API key not valid. Please pass a valid API key."), "AUTH_INVALID_KEY"),
        (gemini_error(403, "permission denied"), "AUTH_INVALID_KEY"),
        (gemini_error(429, "Resource exhausted: quota exceeded"), "QUOTA_EXCEEDED"),
        (gemini_error(429, "too many requests"), "RATE_LIMITED"),
        (gemini_error(503, "service unavailable"), "MODEL_UNAVAILABLE"),
        (gemini_error(404, "model not found"), "MODEL_UNAVAILABLE"),
    ],
)
async def test_error_mapping(monkeypatch, err, category) -> None:
    patch_gemini(monkeypatch, FakeGemini(error=err))
    with pytest.raises(ProviderError) as exc:
        await GeminiAdapter().generate(_req(), "AIza-key")
    assert exc.value.category == category


async def test_list_models_strips_prefix_and_sorts(monkeypatch) -> None:
    patch_gemini(
        monkeypatch, FakeGemini(models=["models/gemini-b", "models/gemini-a"])
    )
    assert await GeminiAdapter().list_models("AIza-key") == ["gemini-a", "gemini-b"]
