"""Deterministic unit tests for the 8-layer ContextBuilder.

These exercise the builder directly against a real session (seeded via ORM), so
layer ordering, cross-model provenance, token-budget trimming priority, the
mandatory-layer guard, and snapshot persistence are all asserted precisely.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.adapters.base import ProviderError
from app.core.security import hash_password
from app.models import (
    Conversation,
    Message,
    Project,
    ProjectDecision,
    ProjectInstruction,
    ProjectTask,
    User,
)
from app.models.context_snapshot import ContextSnapshot
from app.services import context_builder


@pytest.fixture
async def session(test_engine):
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s:
        yield s


async def _seed(
    session,
    *,
    description: str = "A gateway service",
    instructions: str | None = None,
    response_style: str | None = None,
    decisions: tuple = (),  # (title, rationale, status)
    active_task: str | None = None,
    messages: tuple = (),  # dict(role, content, provider?, model_id?)
) -> tuple[Project, Conversation]:
    user = User(email=f"u_{uuid.uuid4().hex}@e.com", password_hash=hash_password("x"))
    session.add(user)
    await session.flush()
    project = Project(
        user_id=user.id,
        name="SentinelGate",
        description=description,
        status="active",
    )
    session.add(project)
    await session.flush()
    if instructions:
        session.add(
            ProjectInstruction(
                project_id=project.id,
                content=instructions,
                response_style=response_style,
                version=1,
                is_active=True,
            )
        )
    for title, rationale, status in decisions:
        session.add(
            ProjectDecision(
                project_id=project.id, title=title, rationale=rationale, status=status
            )
        )
    if active_task:
        session.add(
            ProjectTask(
                project_id=project.id,
                title=active_task,
                status="in_progress",
                is_active_task=True,
            )
        )
    conv = Conversation(project_id=project.id, title="C1")
    session.add(conv)
    await session.flush()
    for i, m in enumerate(messages, start=1):
        session.add(
            Message(
                conversation_id=conv.id,
                sequence_no=i,
                role=m["role"],
                content=m["content"],
                provider=m.get("provider"),
                model_id=m.get("model_id"),
                status="completed",
            )
        )
    await session.commit()
    await session.refresh(conv)
    return project, conv


async def test_layer_order_and_composition(session) -> None:
    _, conv = await _seed(
        session,
        instructions="Always write typed Python.",
        decisions=(("Use Postgres", "ACID + JSONB", "active"),),
        active_task="Ship the ContextBuilder",
        messages=(
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there", "provider": "stub", "model_id": "stub-echo"},
        ),
    )
    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="What next?",
        persist=False,
    )

    # Mandatory layers lead, in priority order.
    assert built.included_layers[0] == "system"
    assert built.included_layers[1] == "project_instructions"
    assert "project_status" in built.included_layers
    assert "active_task" in built.included_layers
    assert "decisions:1" in built.included_layers
    assert "recent_messages:2" in built.included_layers

    # System prompt carries L1..L4 content.
    sp = built.system_prompt
    assert sp.startswith(context_builder.APP_SYSTEM_INSTRUCTIONS[:40])
    assert "# Project: SentinelGate" in sp
    assert "Always write typed Python." in sp
    assert "Active task: Ship the ContextBuilder" in sp
    assert "Use Postgres" in sp

    # messages = recent (2) + current user message (L8, last).
    msgs = built.provider_request.messages
    assert len(msgs) == 3
    assert msgs[-1].role == "user" and msgs[-1].content == "What next?"
    assert built.estimated_input_tokens <= built.token_budget


async def test_cross_model_provenance_tagging_is_transient(session) -> None:
    _, conv = await _seed(
        session,
        messages=(
            {"role": "user", "content": "design it"},
            {"role": "assistant", "content": "OpenAI says do X", "provider": "openai", "model_id": "gpt-x"},
        ),
    )

    # Switching to a DIFFERENT provider tags the prior assistant turn.
    to_claude = await context_builder.build(
        session,
        conversation=conv,
        target_provider="anthropic",
        target_model_id="claude-x",
        user_message_content="continue",
        persist=False,
    )
    assistant_sent = next(m for m in to_claude.provider_request.messages if m.role == "assistant")
    assert assistant_sent.content.startswith("[Previous assistant response via openai/gpt-x]")
    assert "OpenAI says do X" in assistant_sent.content

    # Same provider -> no tag.
    to_openai = await context_builder.build(
        session,
        conversation=conv,
        target_provider="openai",
        target_model_id="gpt-x",
        user_message_content="continue",
        persist=False,
    )
    same = next(m for m in to_openai.provider_request.messages if m.role == "assistant")
    assert same.content == "OpenAI says do X"

    # The canonical DB row is NEVER mutated.
    stored = (
        await session.execute(
            select(Message).where(Message.role == "assistant", Message.conversation_id == conv.id)
        )
    ).scalar_one()
    assert stored.content == "OpenAI says do X"


async def test_system_event_rows_excluded_from_provider_messages(session) -> None:
    _, conv = await _seed(
        session,
        messages=(
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1", "provider": "stub", "model_id": "stub-echo"},
            {"role": "system_event", "content": "Switched to anthropic."},
            {"role": "user", "content": "q2"},
        ),
    )
    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="q3",
        persist=False,
    )
    contents = [m.content for m in built.provider_request.messages]
    assert "Switched to anthropic." not in contents
    # q1, a1, q2 + current q3
    assert contents == ["q1", "a1", "q2", "q3"]


async def test_recent_window_drops_oldest_first(session) -> None:
    long = "word " * 120  # ~600 chars -> large per-message cost
    msgs = tuple({"role": "user", "content": f"[{i}] {long}"} for i in range(8))
    _, conv = await _seed(session, messages=msgs)

    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="now",
        token_budget=1200,
        persist=False,
    )

    recent = [m for m in built.provider_request.messages if m.content != "now"]
    kept_indices = [int(m.content.split("]")[0][1:]) for m in recent]
    omitted = [o for o in built.omitted_items if o["type"] == "recent_message"]

    assert len(recent) < 8  # some were dropped under the tight budget
    assert omitted, "oldest turns should be recorded as omitted"
    # Kept turns are the NEWEST contiguous block; dropped are strictly older.
    assert kept_indices == sorted(kept_indices)
    assert min(kept_indices) > max(o["sequence_no"] for o in omitted) - 1
    dropped_seqs = {o["sequence_no"] for o in omitted}
    kept_seqs = {i + 1 for i in kept_indices}
    assert dropped_seqs.isdisjoint(kept_seqs)
    assert dropped_seqs | kept_seqs == set(range(1, 9))
    assert built.estimated_input_tokens <= 1200


async def test_mandatory_overflow_raises_context_too_large(session) -> None:
    _, conv = await _seed(session, instructions="x" * 4000)
    with pytest.raises(ProviderError) as ei:
        await context_builder.build(
            session,
            conversation=conv,
            target_provider="stub",
            target_model_id="stub-echo",
            user_message_content="hello",
            token_budget=50,  # cannot fit L1 + L2 + L8
            persist=False,
        )
    assert ei.value.category == "CONTEXT_TOO_LARGE"


async def test_snapshot_persisted_on_build(session) -> None:
    _, conv = await _seed(
        session,
        decisions=(("D1", None, "active"),),
        active_task="T1",
        messages=({"role": "user", "content": "hi"},),
    )
    before = await session.scalar(select(func.count()).select_from(ContextSnapshot))

    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="go",
        persist=True,
    )
    await session.commit()

    assert built.snapshot_id is not None
    snap = await session.get(ContextSnapshot, built.snapshot_id)
    assert snap is not None
    assert snap.target_provider == "stub"
    assert snap.token_budget == built.token_budget
    assert snap.estimated_input_tokens == built.estimated_input_tokens
    assert snap.included_layers == built.included_layers

    after = await session.scalar(select(func.count()).select_from(ContextSnapshot))
    assert after == (before or 0) + 1

    # snapshot_summary_dict (the SSE context_ready payload) has the 4 keys.
    summary = built.snapshot_summary_dict()
    assert set(summary) == {
        "snapshot_id",
        "estimated_input_tokens",
        "token_budget",
        "included_layers",
    }


async def test_preview_does_not_persist(session) -> None:
    _, conv = await _seed(session, messages=({"role": "user", "content": "hi"},))
    before = await session.scalar(select(func.count()).select_from(ContextSnapshot))
    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="",
        persist=False,
    )
    await session.commit()
    assert built.snapshot_id is None
    after = await session.scalar(select(func.count()).select_from(ContextSnapshot))
    assert after == (before or 0)


async def test_active_decisions_only(session) -> None:
    """L4 includes only active decisions; superseded ones are excluded."""
    _, conv = await _seed(
        session,
        decisions=(
            ("Keep", "still valid", "active"),
            ("Drop", "obsolete", "superseded"),
        ),
    )
    built = await context_builder.build(
        session,
        conversation=conv,
        target_provider="stub",
        target_model_id="stub-echo",
        user_message_content="go",
        persist=False,
    )
    assert "decisions:1" in built.included_layers
    assert "Keep" in built.system_prompt
    assert "Drop" not in built.system_prompt
