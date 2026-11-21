"""End-to-end Gemini + Claude chat turns, error preservation, and cross-provider IDOR."""

from __future__ import annotations

from httpx import AsyncClient

from tests.fakes import (
    FakeAnthropic,
    FakeGemini,
    anthropic_auth_error,
    fake_anthropic_message,
    fake_gemini_response,
    gemini_error,
    patch_anthropic,
    patch_gemini,
)
from tests.helpers import (
    create_conversation,
    create_project,
    csrf_headers,
    register_user,
)


async def _configure(client, provider: str, api_key: str, model: str):
    await register_user(client)
    h = csrf_headers(client)
    await client.put(
        f"/api/v1/providers/{provider}/key", headers=h, json={"api_key": api_key}
    )
    await client.put(
        f"/api/v1/providers/{provider}/models",
        headers=h,
        json={"enabled_models": [model]},
    )
    return h


async def test_gemini_chat_turn_persists_usage(client: AsyncClient, monkeypatch) -> None:
    h = await _configure(client, "gemini", "AIza-testkey-123456", "gemini-test")
    patch_gemini(
        monkeypatch,
        FakeGemini(
            response=fake_gemini_response(text="Gemini hi", prompt=7, candidates=3, total=10)
        ),
    )
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    r = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Hello", "provider": "gemini", "model_id": "gemini-test"},
    )
    assert r.status_code == 201
    a = r.json()["assistant_message"]
    assert a["provider"] == "gemini"
    assert a["model_id"] == "gemini-test"
    assert a["content"] == "Gemini hi"
    assert a["total_tokens"] == 10
    usage = (await client.get("/api/v1/usage")).json()
    assert usage["total_tokens"] == 10
    assert any(m["provider"] == "gemini" for m in usage["by_model"])


async def test_anthropic_chat_turn_persists_usage(
    client: AsyncClient, monkeypatch
) -> None:
    h = await _configure(client, "anthropic", "sk-ant-testkey-123456", "claude-test")
    patch_anthropic(
        monkeypatch,
        FakeAnthropic(
            message=fake_anthropic_message(text="Claude hi", input_tokens=5, output_tokens=5)
        ),
    )
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    r = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Hello", "provider": "anthropic", "model_id": "claude-test"},
    )
    assert r.status_code == 201
    a = r.json()["assistant_message"]
    assert a["provider"] == "anthropic"
    assert a["content"] == "Claude hi"
    assert a["total_tokens"] == 10
    assert (await client.get("/api/v1/usage")).json()["total_tokens"] == 10


async def test_anthropic_error_preserves_history(
    client: AsyncClient, monkeypatch
) -> None:
    h = await _configure(client, "anthropic", "sk-ant-testkey-123456", "claude-test")
    patch_anthropic(monkeypatch, FakeAnthropic(create_error=anthropic_auth_error()))
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    r = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Hello", "provider": "anthropic", "model_id": "claude-test"},
    )
    assert r.status_code == 502
    assert r.json()["category"] == "AUTH_INVALID_KEY"
    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert [m["role"] for m in msgs] == ["user"]


async def test_gemini_error_preserves_history(
    client: AsyncClient, monkeypatch
) -> None:
    h = await _configure(client, "gemini", "AIza-testkey-123456", "gemini-test")
    patch_gemini(monkeypatch, FakeGemini(error=gemini_error(429, "quota exceeded")))
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    r = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Hi", "provider": "gemini", "model_id": "gemini-test"},
    )
    assert r.status_code == 502
    assert r.json()["category"] == "QUOTA_EXCEEDED"
    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert [m["role"] for m in msgs] == ["user"]


async def test_idor_across_all_providers(make_client) -> None:
    a = await make_client()
    await register_user(a)
    ha = csrf_headers(a)
    for provider, key in [
        ("openai", "sk-A1234567"),
        ("gemini", "AIzaA1234567"),
        ("anthropic", "sk-ant-A1234567"),
    ]:
        await a.put(f"/api/v1/providers/{provider}/key", headers=ha, json={"api_key": key})

    b = await make_client()
    await register_user(b)
    for cfg in (await b.get("/api/v1/providers")).json():
        assert cfg["configured"] is False
        assert cfg["key_hint"] is None

    assert all(c["configured"] for c in (await a.get("/api/v1/providers")).json())
