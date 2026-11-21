"""Multi-model parallel fan-out, partial-failure isolation, context-bloat
prevention, compare/synthesize provenance, and IDOR."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Conversation
from app.services import context_builder
from tests.fakes import (
    FakeAnthropic,
    FakeGemini,
    FakeOpenAI,
    fake_anthropic_message,
    fake_completion,
    fake_gemini_response,
    gemini_error,
    patch_anthropic,
    patch_client,
    patch_gemini,
)
from tests.helpers import (
    create_conversation,
    create_project,
    csrf_headers,
    register_user,
)


@pytest.fixture
async def session(test_engine):
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s:
        yield s


async def _configure(client, provider: str, key: str, model: str) -> None:
    h = csrf_headers(client)
    await client.put(f"/api/v1/providers/{provider}/key", headers=h, json={"api_key": key})
    await client.put(
        f"/api/v1/providers/{provider}/models", headers=h, json={"enabled_models": [model]}
    )


def _patch_all(monkeypatch, *, gemini_err=None) -> None:
    patch_client(monkeypatch, FakeOpenAI(completion=fake_completion(content="A-open", model="gpt-x", prompt=5, completion=5, total=10)))
    patch_anthropic(monkeypatch, FakeAnthropic(message=fake_anthropic_message(text="B-claude", model="claude-x", input_tokens=4, output_tokens=6)))
    if gemini_err is not None:
        patch_gemini(monkeypatch, FakeGemini(error=gemini_err))
    else:
        patch_gemini(monkeypatch, FakeGemini(response=fake_gemini_response(text="C-gemini", prompt=3, candidates=7, total=10)))


_THREE = [
    {"provider": "openai", "model_id": "gpt-x"},
    {"provider": "anthropic", "model_id": "claude-x"},
    {"provider": "gemini", "model_id": "gemini-x"},
]


async def _setup(client) -> tuple[str, str]:
    await register_user(client)
    await _configure(client, "openai", "sk-o-12345678", "gpt-x")
    await _configure(client, "anthropic", "sk-ant-12345678", "claude-x")
    await _configure(client, "gemini", "AIza-12345678", "gemini-x")
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    return pid, cid


async def test_parallel_fanout_group_messages_usage(client, monkeypatch) -> None:
    _, cid = await _setup(client)
    _patch_all(monkeypatch)
    h = csrf_headers(client)

    r = await client.post(
        f"/api/v1/conversations/{cid}/messages/multi",
        headers=h,
        json={"content": "design it", "targets": _THREE},
    )
    assert r.status_code == 201
    body = r.json()
    gid = body["group"]["id"]
    assert body["user_message"]["content"] == "design it"

    resps = body["responses"]
    assert len(resps) == 3
    assert {x["provider"] for x in resps} == {"openai", "anthropic", "gemini"}
    for x in resps:
        assert x["error"] is None
        assert x["message"]["group_id"] == gid
        assert x["message"]["provider"] == x["provider"]

    # The group defaults its continuation to the first success (openai).
    openai_id = next(x["message"]["id"] for x in resps if x["provider"] == "openai")
    assert body["group"]["selected_message_id"] == openai_id

    # Three distinct responses stored canonically + usage recorded per provider.
    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert [m["role"] for m in msgs].count("assistant") == 3
    usage = (await client.get("/api/v1/usage")).json()
    assert usage["total_tokens"] == 30
    assert {m["provider"] for m in usage["by_model"]} == {"openai", "anthropic", "gemini"}


async def test_partial_failure_isolation(client, monkeypatch) -> None:
    _, cid = await _setup(client)
    _patch_all(monkeypatch, gemini_err=gemini_error(429, "rate limited"))
    h = csrf_headers(client)

    r = await client.post(
        f"/api/v1/conversations/{cid}/messages/multi",
        headers=h,
        json={"content": "go", "targets": _THREE},
    )
    assert r.status_code == 201
    resps = {x["provider"]: x for x in r.json()["responses"]}

    # The two successful providers are persisted and returned intact.
    assert resps["openai"]["error"] is None and resps["openai"]["message"]
    assert resps["anthropic"]["error"] is None and resps["anthropic"]["message"]
    # The failed provider returns a categorized error and no message — no fallback.
    assert resps["gemini"]["message"] is None
    assert resps["gemini"]["error"]["category"] in ("RATE_LIMITED", "QUOTA_EXCEEDED")

    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert [m["role"] for m in msgs].count("assistant") == 2
    # The group still has a continuation (first success).
    assert r.json()["group"]["selected_message_id"] is not None


async def test_context_bloat_prevention(client, session, monkeypatch) -> None:
    _, cid = await _setup(client)
    _patch_all(monkeypatch)
    h = csrf_headers(client)

    body = (
        await client.post(
            f"/api/v1/conversations/{cid}/messages/multi",
            headers=h,
            json={"content": "design it", "targets": _THREE},
        )
    ).json()

    # Next turn: the preview counts user + ONE selected response (not all three).
    preview = (await client.get(f"/api/v1/conversations/{cid}/context-preview")).json()
    assert "recent_messages:2" in preview["included_layers"]

    # Direct build: only the selected (openai) response reaches L7.
    conv = await session.get(Conversation, uuid.UUID(cid))
    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="next",
        persist=False,
    )
    l7 = "\n".join(m.content for m in built.provider_request.messages if m.content != "next")
    assert "A-open" in l7
    assert "B-claude" not in l7
    assert "C-gemini" not in l7

    # Every parallel response remains stored in PostgreSQL.
    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert sum(1 for m in msgs if m["role"] == "assistant") == 3

    # Re-selecting Claude swaps which response feeds context (count stays 2).
    claude_id = next(
        x["message"]["id"] for x in body["responses"] if x["provider"] == "anthropic"
    )
    sel = await client.patch(
        f"/api/v1/message-groups/{body['group']['id']}/select",
        headers=h,
        json={"message_id": claude_id},
    )
    assert sel.status_code == 200
    assert sel.json()["selected_message_id"] == claude_id
    await session.rollback()  # fresh read snapshot
    built2 = await context_builder.build(
        session,
        conversation=await session.get(Conversation, uuid.UUID(cid)),
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="next",
        persist=False,
    )
    l7b = "\n".join(m.content for m in built2.provider_request.messages if m.content != "next")
    assert "B-claude" in l7b
    assert "A-open" not in l7b


async def test_compare_and_synthesize_provenance(client, monkeypatch) -> None:
    _, cid = await _setup(client)
    _patch_all(monkeypatch)
    h = csrf_headers(client)

    body = (
        await client.post(
            f"/api/v1/conversations/{cid}/messages/multi",
            headers=h,
            json={
                "content": "design it",
                "targets": [
                    {"provider": "openai", "model_id": "gpt-x"},
                    {"provider": "anthropic", "model_id": "claude-x"},
                ],
            },
        )
    ).json()
    oa_id = next(x["message"]["id"] for x in body["responses"] if x["provider"] == "openai")
    cl_id = next(x["message"]["id"] for x in body["responses"] if x["provider"] == "anthropic")
    gid = body["group"]["id"]

    # Gemini critiques OpenAI's response.
    rc = await client.post(
        f"/api/v1/conversations/{cid}/compare",
        headers=h,
        json={
            "target_provider": "gemini",
            "target_model_id": "gemini-x",
            "subject_message_id": oa_id,
            "critique_focus": "security",
        },
    )
    assert rc.status_code == 201
    cmsg = rc.json()["message"]
    assert cmsg["provider"] == "gemini"
    assert cmsg["metadata_json"]["operation"] == "critique"
    assert cmsg["metadata_json"]["derived_from_message_ids"] == [oa_id]
    assert cmsg["metadata_json"]["subject"]["provider"] == "openai"
    # A critique is analysis, not a continuation — selection unchanged.
    assert rc.json()["group"]["selected_message_id"] == oa_id

    # Gemini synthesizes both responses → becomes the group's continuation.
    rs = await client.post(
        f"/api/v1/conversations/{cid}/synthesize",
        headers=h,
        json={
            "target_provider": "gemini",
            "target_model_id": "gemini-x",
            "source_message_ids": [oa_id, cl_id],
        },
    )
    assert rs.status_code == 201
    smsg = rs.json()["message"]
    assert smsg["metadata_json"]["operation"] == "synthesis"
    assert set(smsg["metadata_json"]["derived_from_message_ids"]) == {oa_id, cl_id}
    assert smsg["metadata_json"]["synthesizer"]["provider"] == "gemini"
    assert rs.json()["group"]["selected_message_id"] == smsg["id"]
    assert smsg["group_id"] == gid

    # Usage recorded for the gemini critique + synthesis calls.
    usage = (await client.get("/api/v1/usage")).json()
    assert any(m["provider"] == "gemini" for m in usage["by_model"])


async def test_compare_provider_error_returns_502(client, monkeypatch) -> None:
    _, cid = await _setup(client)
    _patch_all(monkeypatch)
    h = csrf_headers(client)
    body = (
        await client.post(
            f"/api/v1/conversations/{cid}/messages/multi",
            headers=h,
            json={"content": "x", "targets": [{"provider": "openai", "model_id": "gpt-x"}]},
        )
    ).json()
    oa_id = body["responses"][0]["message"]["id"]

    patch_gemini(monkeypatch, FakeGemini(error=gemini_error(429, "rate limited")))
    r = await client.post(
        f"/api/v1/conversations/{cid}/compare",
        headers=h,
        json={"target_provider": "gemini", "target_model_id": "gemini-x", "subject_message_id": oa_id},
    )
    assert r.status_code == 502
    assert r.json()["category"] in ("RATE_LIMITED", "QUOTA_EXCEEDED")


async def test_multimodel_idor(make_client, monkeypatch) -> None:
    a = await make_client()
    await register_user(a)
    await _configure(a, "openai", "sk-o-12345678", "gpt-x")
    patch_client(monkeypatch, FakeOpenAI(completion=fake_completion(content="A", model="gpt-x")))
    pid = await create_project(a)
    cid = await create_conversation(a, pid)
    body = (
        await a.post(
            f"/api/v1/conversations/{cid}/messages/multi",
            headers=csrf_headers(a),
            json={"content": "x", "targets": [{"provider": "openai", "model_id": "gpt-x"}]},
        )
    ).json()
    gid = body["group"]["id"]
    mid = body["responses"][0]["message"]["id"]

    b = await make_client()
    await register_user(b)
    hb = csrf_headers(b)

    assert (
        await b.post(
            f"/api/v1/conversations/{cid}/messages/multi",
            headers=hb,
            json={"content": "x", "targets": [{"provider": "stub", "model_id": "stub-echo"}]},
        )
    ).status_code == 404
    assert (
        await b.get(f"/api/v1/conversations/{cid}/message-groups")
    ).status_code == 404
    assert (
        await b.patch(
            f"/api/v1/message-groups/{gid}/select", headers=hb, json={"message_id": mid}
        )
    ).status_code == 404
    assert (
        await b.post(
            f"/api/v1/conversations/{cid}/compare",
            headers=hb,
            json={"target_provider": "stub", "target_model_id": "stub-echo", "subject_message_id": mid},
        )
    ).status_code == 404
    assert (
        await b.post(
            f"/api/v1/conversations/{cid}/synthesize",
            headers=hb,
            json={
                "target_provider": "stub",
                "target_model_id": "stub-echo",
                "source_message_ids": [mid, mid],
            },
        )
    ).status_code == 404

    # A's group + responses are intact.
    assert len((await a.get(f"/api/v1/conversations/{cid}/message-groups")).json()) == 1
