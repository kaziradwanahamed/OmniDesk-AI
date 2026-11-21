"""Message write-ahead persistence, ordering, stub round-trip, error preservation."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import create_conversation, create_project, csrf_headers, register_user


async def test_send_message_round_trip_and_ordering(client: AsyncClient) -> None:
    await register_user(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    h = csrf_headers(client)

    resp = await client.post(
        f"/api/v1/conversations/{cid}/messages", headers=h, json={"content": "Hello"}
    )
    assert resp.status_code == 201
    body = resp.json()

    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "Hello"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["provider"] == "stub"
    assert body["assistant_message"]["model_id"] == "stub-echo"
    assert "[stub-echo]" in body["assistant_message"]["content"]
    assert (
        body["assistant_message"]["sequence_no"]
        == body["user_message"]["sequence_no"] + 1
    )
    # No fabricated usage from the stub.
    assert body["assistant_message"]["total_tokens"] is None

    messages = await client.get(f"/api/v1/conversations/{cid}/messages")
    assert messages.status_code == 200
    seqs = [m["sequence_no"] for m in messages.json()]
    assert seqs == sorted(seqs)
    assert len(messages.json()) == 2


async def test_messages_persist_across_sends(client: AsyncClient) -> None:
    await register_user(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    h = csrf_headers(client)

    await client.post(
        f"/api/v1/conversations/{cid}/messages", headers=h, json={"content": "one"}
    )
    await client.post(
        f"/api/v1/conversations/{cid}/messages", headers=h, json={"content": "two"}
    )
    messages = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert [m["sequence_no"] for m in messages] == [1, 2, 3, 4]
    assert [m["role"] for m in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


async def test_adapter_error_preserves_user_message_and_history(
    client: AsyncClient,
) -> None:
    await register_user(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    h = csrf_headers(client)

    # One good turn first.
    await client.post(
        f"/api/v1/conversations/{cid}/messages", headers=h, json={"content": "hi"}
    )
    # Trigger a simulated adapter failure.
    failed = await client.post(
        f"/api/v1/conversations/{cid}/messages",
        headers=h,
        json={"content": "__fail__"},
    )
    assert failed.status_code == 502
    assert failed.json()["category"] == "MODEL_UNAVAILABLE"

    messages = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    roles = [m["role"] for m in messages]
    contents = [m["content"] for m in messages]
    # Prior history intact + the failed user message persisted; no assistant reply for it.
    assert roles == ["user", "assistant", "user"]
    assert "__fail__" in contents
    assert len(messages) == 3


async def test_send_requires_csrf(client: AsyncClient) -> None:
    await register_user(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    resp = await client.post(
        f"/api/v1/conversations/{cid}/messages", json={"content": "x"}
    )
    assert resp.status_code == 403
