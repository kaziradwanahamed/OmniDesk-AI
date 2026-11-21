"""End-to-end OpenAI chat turn (mocked SDK): persistence, usage, error preservation."""

from __future__ import annotations

from httpx import AsyncClient

from tests.fakes import FakeOpenAI, auth_error, fake_completion, patch_client
from tests.helpers import (
    create_conversation,
    create_project,
    csrf_headers,
    register_user,
)


async def _configure_openai(client, monkeypatch, *, completion=None, error=None):
    await register_user(client)
    h = csrf_headers(client)
    await client.put(
        "/api/v1/providers/openai/key", headers=h, json={"api_key": "sk-testkey123456"}
    )
    await client.put(
        "/api/v1/providers/openai/models",
        headers=h,
        json={"enabled_models": ["gpt-test"]},
    )
    patch_client(monkeypatch, FakeOpenAI(completion=completion, create_error=error))
    return h


async def test_openai_chat_turn_persists_and_records_usage(
    client: AsyncClient, monkeypatch
) -> None:
    h = await _configure_openai(
        client,
        monkeypatch,
        completion=fake_completion(
            content="Hi there!", model="gpt-test", prompt=11, completion=4, total=15
        ),
    )
    pid = await create_project(client)
    cid = await create_conversation(client, pid)

    resp = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Hello", "provider": "openai", "model_id": "gpt-test"},
    )
    assert resp.status_code == 201
    assistant = resp.json()["assistant_message"]
    assert assistant["provider"] == "openai"
    assert assistant["model_id"] == "gpt-test"
    assert assistant["content"] == "Hi there!"
    assert assistant["input_tokens"] == 11
    assert assistant["total_tokens"] == 15

    usage = (await client.get("/api/v1/usage")).json()
    assert usage["total_tokens"] == 15
    assert any(
        m["provider"] == "openai" and m["model_id"] == "gpt-test"
        for m in usage["by_model"]
    )


async def test_openai_provider_error_preserves_history(
    client: AsyncClient, monkeypatch
) -> None:
    h = await _configure_openai(client, monkeypatch, error=auth_error())
    pid = await create_project(client)
    cid = await create_conversation(client, pid)

    resp = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Hello", "provider": "openai", "model_id": "gpt-test"},
    )
    assert resp.status_code == 502
    assert resp.json()["category"] == "AUTH_INVALID_KEY"

    # Write-ahead: the user message is preserved; no assistant reply, no usage.
    messages = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert [m["role"] for m in messages] == ["user"]
    assert messages[0]["content"] == "Hello"
    assert (await client.get("/api/v1/usage")).json()["total_tokens"] == 0


async def test_send_without_configured_key_fails_before_persisting(
    client: AsyncClient,
) -> None:
    await register_user(client)
    h = csrf_headers(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)

    resp = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Hello", "provider": "openai", "model_id": "gpt-test"},
    )
    assert resp.status_code == 502
    assert resp.json()["category"] == "AUTH_INVALID_KEY"
    # Pre-flight misconfig: nothing persisted.
    assert (await client.get(f"/api/v1/conversations/{cid}/messages")).json() == []
