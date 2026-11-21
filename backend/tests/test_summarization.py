"""Conversation summarization (L6): canonical preservation, L6/L7 dedup, rolling
re-summarization, user edits, budget priority, failure resilience, and IDOR."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.adapters.base import ProviderError
from app.core.security import hash_password
from app.models import Conversation, Message, Project, User
from app.models.context_summary import ConversationSummary
from app.services import context_builder, summarization_service
from tests.fakes import FakeOpenAI, fake_completion, patch_client, rate_limit_error
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


async def _mk_conversation(session) -> tuple[User, Conversation]:
    user = User(email=f"u_{uuid.uuid4().hex}@e.com", password_hash=hash_password("x"))
    session.add(user)
    await session.flush()
    project = Project(user_id=user.id, name="SentinelGate", status="active")
    session.add(project)
    await session.flush()
    conv = Conversation(project_id=project.id, title="C1")
    session.add(conv)
    await session.flush()
    await session.commit()
    await session.refresh(conv)
    return user, conv


async def _seed_messages(session, conversation_id, n, start=1, prefix="msg"):
    cid = conversation_id if isinstance(conversation_id, uuid.UUID) else uuid.UUID(conversation_id)
    for i in range(n):
        seq = start + i
        role = "user" if seq % 2 == 1 else "assistant"
        session.add(
            Message(
                conversation_id=cid,
                sequence_no=seq,
                role=role,
                content=f"{prefix}-{seq}",
                provider=("openai" if role == "assistant" else None),
                model_id=("gpt-x" if role == "assistant" else None),
                status="completed",
            )
        )
    await session.commit()


# ------------------------------- service level -------------------------------


async def test_summarize_preserves_canonical_messages(session) -> None:
    user, conv = await _mk_conversation(session)
    await _seed_messages(session, conv.id, 20)

    before = {
        m.id: (m.sequence_no, m.content)
        for m in (
            await session.execute(
                select(Message).where(Message.conversation_id == conv.id)
            )
        ).scalars()
    }

    summary = await summarization_service.summarize(session, conv, user.id)  # stub
    assert summary is not None
    assert summary.version == 1
    # Default tail=8 → covers up to sequence 12 (20 - 8), 12 messages covered.
    assert summary.covers_up_to_sequence == 12
    assert summary.covered_message_count == 12
    assert summary.content  # non-empty
    assert summary.is_active is True

    after = {
        m.id: (m.sequence_no, m.content)
        for m in (
            await session.execute(
                select(Message).where(Message.conversation_id == conv.id)
            )
        ).scalars()
    }
    # Every canonical row is byte-for-byte unchanged and none were deleted/added.
    assert after == before
    assert len(after) == 20


async def test_context_builder_l6_l7_deduplication(session) -> None:
    user, conv = await _mk_conversation(session)
    await _seed_messages(session, conv.id, 20)
    # A user-authored summary covering up to sequence 12 (no provider call).
    await summarization_service.update_summary(session, conv, "SUMMARY-MARKER-XYZ")

    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="what next?",
        persist=False,
    )

    # L6 summary present in the system prompt and audited.
    assert "SUMMARY-MARKER-XYZ" in built.system_prompt
    assert any(layer.startswith("summary:v") for layer in built.included_layers)

    # L7 holds ONLY the post-cutoff tail (seq 13-20) + the current message — the
    # covered messages (seq <= 12) are represented by L6, never duplicated.
    # (Assistant turns may carry a provenance prefix, so match as substrings.)
    l7 = "\n".join(
        m.content for m in built.provider_request.messages if m.content != "what next?"
    )
    assert "msg-12" not in l7  # covered by the summary, excluded from L7
    assert "msg-13" in l7
    assert "msg-20" in l7
    assert built.recent_message_count == 8
    assert "recent_messages:8" in built.included_layers


async def test_rolling_resummarization_and_user_edit(session) -> None:
    user, conv = await _mk_conversation(session)
    await _seed_messages(session, conv.id, 20)

    v1 = await summarization_service.summarize(session, conv, user.id)
    assert v1.version == 1 and v1.covers_up_to_sequence == 12
    assert v1.user_edited is False and v1.provider == "stub"

    # Age in 10 more messages, then re-summarize → folds prior + newly aged.
    await _seed_messages(session, conv.id, 10, start=21)
    v2 = await summarization_service.summarize(session, conv, user.id)
    assert v2.version == 2
    assert v2.covers_up_to_sequence == 22  # 30 - 8
    assert v2.user_edited is False

    # Manual user correction supersedes with a new user-edited version.
    v3 = await summarization_service.update_summary(session, conv, "Human-corrected summary.")
    assert v3.version == 3
    assert v3.user_edited is True
    assert v3.content == "Human-corrected summary."
    assert v3.covers_up_to_sequence == 22  # inherits the active coverage

    # Exactly one active row; full version history retained (3 rows).
    active = await summarization_service.get_active_summary(session, conv.id)
    assert active.id == v3.id
    total = await session.scalar(
        select(func.count())
        .select_from(ConversationSummary)
        .where(ConversationSummary.conversation_id == conv.id)
    )
    assert total == 3


async def test_tight_budget_priority_order(session) -> None:
    """Under a tight budget, pinned memory (instructions, active task, decisions)
    is kept while the summary (L6) and/or oldest recent turns (L7) are trimmed."""
    user = User(email=f"u_{uuid.uuid4().hex}@e.com", password_hash=hash_password("x"))
    session.add(user)
    await session.flush()
    project = Project(
        user_id=user.id,
        name="P",
        description="short",
        status="active",
    )
    session.add(project)
    await session.flush()
    from app.models import ProjectDecision, ProjectTask

    session.add(ProjectTask(project_id=project.id, title="ACTIVE-TASK", is_active_task=True))
    session.add(ProjectDecision(project_id=project.id, title="KEY-DECISION", status="active"))
    conv = Conversation(project_id=project.id, title="C")
    session.add(conv)
    await session.flush()
    await session.commit()
    await session.refresh(conv)

    await _seed_messages(session, conv.id, 12, prefix="word word word")
    # A large summary that cannot fully fit the tight budget.
    await summarization_service.update_summary(session, conv, "LONG " * 400)

    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="go",
        token_budget=400,
        persist=False,
    )

    # Pinned memory survives the squeeze.
    assert "active_task" in built.included_layers
    assert any(x.startswith("decisions:") for x in built.included_layers)
    assert "ACTIVE-TASK" in built.system_prompt
    assert "KEY-DECISION" in built.system_prompt
    # Something was trimmed/omitted, and the estimate honors the budget.
    assert built.omitted_items
    assert built.estimated_input_tokens <= 400


async def test_summarization_failure_preserves_state(session, monkeypatch) -> None:
    user = User(email=f"u_{uuid.uuid4().hex}@e.com", password_hash=hash_password("x"))
    session.add(user)
    await session.flush()
    project = Project(user_id=user.id, name="P", status="active")
    session.add(project)
    await session.flush()
    conv = Conversation(
        project_id=project.id, title="C", active_provider="openai", active_model_id="gpt-x"
    )
    session.add(conv)
    await session.flush()
    await session.commit()
    await session.refresh(conv)
    await _seed_messages(session, conv.id, 20)

    # Configure the user's OpenAI key (resolution precedes the mocked call).
    from app.services import provider_key_service

    await provider_key_service.set_key(session, user.id, "openai", "sk-test-123456")
    await provider_key_service.set_enabled_models(session, user.id, "openai", ["gpt-x"])

    # First summarization succeeds (v1).
    patch_client(monkeypatch, FakeOpenAI(completion=fake_completion(content="SUMMARY V1", model="gpt-x")))
    v1 = await summarization_service.summarize(session, conv, user.id, "openai", "gpt-x")
    assert v1.version == 1

    # Age in more messages; the next provider call rate-limits.
    await _seed_messages(session, conv.id, 10, start=21)
    patch_client(monkeypatch, FakeOpenAI(create_error=rate_limit_error()))
    with pytest.raises(ProviderError) as ei:
        await summarization_service.summarize(session, conv, user.id, "openai", "gpt-x")
    assert ei.value.category == "RATE_LIMITED"

    # The active summary is still v1 and canonical history is intact.
    active = await summarization_service.get_active_summary(session, conv.id)
    assert active.version == 1 and active.content == "SUMMARY V1"
    msg_count = await session.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conv.id)
    )
    assert msg_count == 30
    # No silent provider switch.
    await session.refresh(conv)
    assert conv.active_provider == "openai"


# -------------------------------- endpoint level -----------------------------


async def test_summary_endpoints_happy_path(client, session) -> None:
    await register_user(client)
    h = csrf_headers(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    await _seed_messages(session, cid, 20)

    # No summary yet.
    r0 = await client.get(f"/api/v1/conversations/{cid}/summary")
    assert r0.status_code == 200
    assert r0.json()["summary"] is None
    assert r0.json()["needs_summary"] is True  # 20 unsummarized > 12 threshold

    # Refresh (uses the stub default provider — no key required).
    r1 = await client.post(f"/api/v1/conversations/{cid}/summary/refresh", headers=h, json={})
    assert r1.status_code == 200
    body = r1.json()
    assert body["summary"]["version"] == 1
    assert body["summary"]["covers_up_to_sequence"] == 12
    assert body["unsummarized_count"] == 8
    assert body["needs_summary"] is False

    # Edit.
    r2 = await client.put(
        f"/api/v1/conversations/{cid}/summary", headers=h, json={"content": "Edited."}
    )
    assert r2.status_code == 200
    assert r2.json()["user_edited"] is True
    assert r2.json()["content"] == "Edited."
    assert r2.json()["version"] == 2

    # Clear (canonical messages untouched).
    r3 = await client.delete(f"/api/v1/conversations/{cid}/summary", headers=h)
    assert r3.status_code == 204
    assert (await client.get(f"/api/v1/conversations/{cid}/summary")).json()["summary"] is None
    msgs = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
    assert len(msgs) == 20


async def test_summary_refresh_requires_csrf(client, session) -> None:
    await register_user(client)
    pid = await create_project(client)
    cid = await create_conversation(client, pid)
    r = await client.post(f"/api/v1/conversations/{cid}/summary/refresh", json={})
    assert r.status_code == 403


async def test_summary_endpoints_idor(make_client, test_engine) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)

    a = await make_client()
    await register_user(a)
    pid = await create_project(a)
    cid = await create_conversation(a, pid)
    async with sm() as s:
        await _seed_messages(s, cid, 20)
    await a.post(f"/api/v1/conversations/{cid}/summary/refresh", headers=csrf_headers(a), json={})

    b = await make_client()
    await register_user(b)
    hb = csrf_headers(b)
    assert (await b.get(f"/api/v1/conversations/{cid}/summary")).status_code == 404
    assert (
        await b.post(f"/api/v1/conversations/{cid}/summary/refresh", headers=hb, json={})
    ).status_code == 404
    assert (
        await b.put(
            f"/api/v1/conversations/{cid}/summary", headers=hb, json={"content": "x"}
        )
    ).status_code == 404
    assert (
        await b.delete(f"/api/v1/conversations/{cid}/summary", headers=hb)
    ).status_code == 404

    # A's summary is intact.
    assert (await a.get(f"/api/v1/conversations/{cid}/summary")).json()["summary"]["version"] == 1
