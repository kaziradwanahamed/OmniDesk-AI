"""Seamless manual model switching across one canonical conversation.

Covers: OpenAI -> Claude -> Gemini within a single conversation (never
recreated), system_event dividers, cross-model provenance reaching each vendor
request, zero history loss, failure preservation, the context-preview dry run,
and the context-snapshot inspector (with IDOR)."""

from __future__ import annotations

from httpx import AsyncClient

from app.services import provider_key_service
from tests.fakes import (
    FakeAnthropic,
    FakeGemini,
    FakeOpenAI,
    anthropic_auth_error,
    fake_anthropic_message,
    fake_completion,
    fake_gemini_response,
    patch_anthropic,
    patch_client,
    patch_gemini,
    rate_limit_error,
)
from tests.helpers import (
    create_conversation,
    create_project,
    csrf_headers,
    register_user,
)


async def _configure(client: AsyncClient, provider: str, key: str, model: str) -> None:
    h = csrf_headers(client)
    await client.put(
        f"/api/v1/providers/{provider}/key", headers=h, json={"api_key": key}
    )
    await client.put(
        f"/api/v1/providers/{provider}/models",
        headers=h,
        json={"enabled_models": [model]},
    )


def _gemini_texts(fake: FakeGemini) -> list[str]:
    contents = fake.aio.models.last_kwargs["contents"]
    return [p.text for c in contents for p in c.parts]


async def test_seamless_switch_three_providers(
    client: AsyncClient, monkeypatch
) -> None:
    await register_user(client)
    h = csrf_headers(client)
    await _configure(client, "openai", "sk-o-12345678", "gpt-x")
    await _configure(client, "anthropic", "sk-ant-12345678", "claude-x")
    await _configure(client, "gemini", "AIza-12345678", "gemini-x")

    pid = await create_project(client)
    cid = await create_conversation(client, pid)

    openai_fake = FakeOpenAI(completion=fake_completion(content="OpenAI answer", model="gpt-x"))
    anthropic_fake = FakeAnthropic(message=fake_anthropic_message(text="Claude answer", model="claude-x"))
    gemini_fake = FakeGemini(response=fake_gemini_response(text="Gemini answer"))
    patch_client(monkeypatch, openai_fake)
    patch_anthropic(monkeypatch, anthropic_fake)
    patch_gemini(monkeypatch, gemini_fake)

    # --- Turn 1: OpenAI ---
    r1 = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Design the gateway", "provider": "openai", "model_id": "gpt-x"},
    )
    assert r1.status_code == 201
    a1 = r1.json()["assistant_message"]
    assert a1["provider"] == "openai"
    assert a1["context_snapshot_id"] is not None

    # --- Switch to Claude ---
    sw1 = await client.patch(
        f"/api/v1/conversations/{cid}/model",
        headers=h,
        json={"provider": "anthropic", "model_id": "claude-x"},
    )
    assert sw1.status_code == 200
    ev1 = sw1.json()["event"]
    assert ev1["role"] == "system_event"
    assert ev1["metadata_json"]["event"] == "model_switched"
    assert ev1["metadata_json"]["from"]["provider"] == "openai"
    assert ev1["metadata_json"]["to"]["provider"] == "anthropic"
    assert sw1.json()["conversation"]["active_provider"] == "anthropic"

    # --- Turn 2: Claude (uses the active model; no override) ---
    r2 = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Add rate limiting"},
    )
    assert r2.status_code == 201
    assert r2.json()["assistant_message"]["provider"] == "anthropic"
    # Provenance for the prior OpenAI turn reached the Anthropic request body.
    claude_msgs = anthropic_fake.last_kwargs["messages"]
    assert any(
        "[Previous assistant response via openai/" in m["content"] for m in claude_msgs
    )

    # --- Switch to Gemini ---
    sw2 = await client.patch(
        f"/api/v1/conversations/{cid}/model",
        headers=h,
        json={"provider": "gemini", "model_id": "gemini-x"},
    )
    assert sw2.status_code == 200

    # --- Turn 3: Gemini ---
    r3 = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "Summarize the design"},
    )
    assert r3.status_code == 201
    assert r3.json()["assistant_message"]["provider"] == "gemini"
    gem_texts = _gemini_texts(gemini_fake)
    flat = "\n".join(gem_texts)
    assert "[Previous assistant response via openai/" in flat
    assert "[Previous assistant response via anthropic/" in flat

    # --- One canonical conversation, full history, dividers in place ---
    all_msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    roles = [m["role"] for m in all_msgs]
    assert roles.count("user") == 3
    assert roles.count("assistant") == 3
    assert roles.count("system_event") == 2
    assert all(m["conversation_id"] == cid for m in all_msgs)
    # Provenance tags live only in transient requests — never in stored rows.
    assert not any("[Previous assistant response" in m["content"] for m in all_msgs)


async def test_switch_to_unconfigured_provider_is_rejected(
    client: AsyncClient, monkeypatch
) -> None:
    # Ensure no server-env fallback masks the missing key.
    monkeypatch.setitem(provider_key_service._ENV_FALLBACK, "gemini", lambda: None)
    await register_user(client)
    h = csrf_headers(client)
    await _configure(client, "openai", "sk-o-12345678", "gpt-x")
    pid = await create_project(client)
    cid = await create_conversation(client, pid)

    r = await client.patch(
        f"/api/v1/conversations/{cid}/model",
        headers=h,
        json={"provider": "gemini", "model_id": "gemini-x"},
    )
    assert r.status_code == 400
    assert r.json()["category"] in ("AUTH_INVALID_KEY", "MODEL_UNAVAILABLE")

    # The conversation's active model is unchanged and no divider was logged.
    conv = (await client.get(f"/api/v1/conversations/{cid}")).json()
    assert conv["active_provider"] != "gemini"
    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert not any(m["role"] == "system_event" for m in msgs)


async def test_switch_then_provider_failure_preserves_history(
    client: AsyncClient, monkeypatch
) -> None:
    await register_user(client)
    h = csrf_headers(client)
    await _configure(client, "openai", "sk-o-12345678", "gpt-x")
    await _configure(client, "anthropic", "sk-ant-12345678", "claude-x")
    pid = await create_project(client)
    cid = await create_conversation(client, pid)

    patch_client(monkeypatch, FakeOpenAI(completion=fake_completion(content="ok", model="gpt-x")))
    patch_anthropic(monkeypatch, FakeAnthropic(create_error=anthropic_auth_error()))

    # Turn 1 OpenAI succeeds.
    await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "first", "provider": "openai", "model_id": "gpt-x"},
    )
    # Switch to Claude, then a failing turn.
    await client.patch(
        f"/api/v1/conversations/{cid}/model",
        headers=h,
        json={"provider": "anthropic", "model_id": "claude-x"},
    )
    r = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "second"},
    )
    assert r.status_code == 502
    assert r.json()["category"] == "AUTH_INVALID_KEY"

    # History intact: user1, assistant1(openai), system_event, user2 (write-ahead);
    # no assistant row for the failed turn.
    roles = [m["role"] for m in (await client.get(f"/api/v1/conversations/{cid}/messages")).json()]
    assert roles == ["user", "assistant", "system_event", "user"]


async def test_noop_switch_returns_no_event(client: AsyncClient, monkeypatch) -> None:
    await register_user(client)
    h = csrf_headers(client)
    await _configure(client, "openai", "sk-o-12345678", "gpt-x")
    patch_client(monkeypatch, FakeOpenAI(completion=fake_completion(content="ok", model="gpt-x")))
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "hi", "provider": "openai", "model_id": "gpt-x"},
    )
    # Switch to the model that is already active -> no divider row.
    r = await client.patch(
        f"/api/v1/conversations/{cid}/model",
        headers=h,
        json={"provider": "openai", "model_id": "gpt-x"},
    )
    assert r.status_code == 200
    assert r.json()["event"] is None
    roles = [m["role"] for m in (await client.get(f"/api/v1/conversations/{cid}/messages")).json()]
    assert "system_event" not in roles


async def test_switch_and_retry_reuses_user_message(
    client: AsyncClient, monkeypatch
) -> None:
    await register_user(client)
    h = csrf_headers(client)
    await _configure(client, "openai", "sk-o-12345678", "gpt-x")
    await _configure(client, "anthropic", "sk-ant-12345678", "claude-x")
    pid = await create_project(client)
    cid = await create_conversation(client, pid)

    # OpenAI rate-limits; the user message is saved (write-ahead).
    patch_client(monkeypatch, FakeOpenAI(create_error=rate_limit_error()))
    patch_anthropic(
        monkeypatch,
        FakeAnthropic(message=fake_anthropic_message(text="Claude recovery", model="claude-x")),
    )
    fail = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "do the thing", "provider": "openai", "model_id": "gpt-x"},
    )
    assert fail.status_code == 502
    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert [m["role"] for m in msgs] == ["user"]
    failed_user_id = msgs[0]["id"]

    # Switch to Claude, then "Switch Model & Retry" reusing the saved user row.
    await client.patch(
        f"/api/v1/conversations/{cid}/model",
        headers=h,
        json={"provider": "anthropic", "model_id": "claude-x"},
    )
    retry = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={
            "content": "do the thing",
            "provider": "anthropic",
            "model_id": "claude-x",
            "retry_message_id": failed_user_id,
        },
    )
    assert retry.status_code == 201
    assert retry.json()["assistant_message"]["provider"] == "anthropic"
    # The saved user message is reused, not duplicated.
    assert retry.json()["user_message"]["id"] == failed_user_id

    roles = [m["role"] for m in (await client.get(f"/api/v1/conversations/{cid}/messages")).json()]
    assert roles.count("user") == 1
    assert roles.count("assistant") == 1
    assert roles.count("system_event") == 1


async def test_context_preview_dry_run(client: AsyncClient, monkeypatch) -> None:
    await register_user(client)
    h = csrf_headers(client)
    await _configure(client, "openai", "sk-o-12345678", "gpt-x")
    patch_client(monkeypatch, FakeOpenAI(completion=fake_completion(content="ok", model="gpt-x")))
    pid = await create_project(client)
    # Seed some project memory so the preview reflects real layers.
    await client.post(
        f"/api/v1/projects/{pid}/decisions", headers=h, json={"title": "Use Fernet"}
    )
    cid = await create_conversation(client, pid)
    await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "hello", "provider": "openai", "model_id": "gpt-x"},
    )

    preview = await client.get(f"/api/v1/conversations/{cid}/context-preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["token_budget"] == 16000
    assert "system" in body["included_layers"]
    assert "project_instructions" in body["included_layers"]
    assert "decisions:1" in body["included_layers"]
    assert body["recent_message_count"] >= 2  # prior user + assistant turns
    assert body["estimated_input_tokens"] <= body["token_budget"]
    # Nothing was persisted by the dry run — no snapshot leaks into the preview.
    assert "snapshot_id" not in body


async def test_context_snapshot_fetch_and_idor(
    make_client, monkeypatch
) -> None:
    a = await make_client()
    await register_user(a)
    ha = csrf_headers(a)
    await _configure(a, "openai", "sk-o-12345678", "gpt-x")
    patch_client(monkeypatch, FakeOpenAI(completion=fake_completion(content="ok", model="gpt-x")))
    pid = await create_project(a)
    cid = await create_conversation(a, pid)
    resp = await a.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=ha,
        json={"content": "hello", "provider": "openai", "model_id": "gpt-x"},
    )
    sid = resp.json()["assistant_message"]["context_snapshot_id"]
    assert sid is not None

    # Owner can inspect the exact context that was sent.
    got = await a.get(f"/api/v1/context-snapshots/{sid}")
    assert got.status_code == 200
    assert got.json()["target_provider"] == "openai"
    assert "system" in got.json()["included_layers"]

    # A different user cannot (404, never 403 — no existence leak).
    b = await make_client()
    await register_user(b)
    assert (await b.get(f"/api/v1/context-snapshots/{sid}")).status_code == 404
