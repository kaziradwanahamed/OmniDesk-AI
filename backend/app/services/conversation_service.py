"""Conversation CRUD and the write-ahead message send pipeline."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import CanonicalMessage, ProviderRequest
from app.adapters.registry import get_adapter
from app.models.conversation import Conversation, Message
from app.services import project_service

DEFAULT_PROVIDER = "stub"
DEFAULT_MODEL = "stub-echo"


async def list_conversations(
    db: AsyncSession, project_id: uuid.UUID
) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_conversation(
    db: AsyncSession, project_id: uuid.UUID, title: str
) -> Conversation:
    conv = Conversation(project_id=project_id, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def rename_conversation(
    db: AsyncSession, conversation: Conversation, title: str
) -> Conversation:
    conversation.title = title
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def delete_conversation(db: AsyncSession, conversation: Conversation) -> None:
    await db.delete(conversation)
    await db.commit()


async def list_messages(
    db: AsyncSession, conversation_id: uuid.UUID
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence_no.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _next_sequence(db: AsyncSession, conversation_id: uuid.UUID) -> int:
    # Lock the conversation row so concurrent sends can't collide on sequence_no.
    await db.execute(
        select(Conversation.id)
        .where(Conversation.id == conversation_id)
        .with_for_update()
    )
    current = await db.scalar(
        select(func.coalesce(func.max(Message.sequence_no), 0)).where(
            Message.conversation_id == conversation_id
        )
    )
    return int(current or 0) + 1


async def _append(
    db: AsyncSession, conversation_id: uuid.UUID, role: str, content: str, **fields
) -> Message:
    seq = await _next_sequence(db, conversation_id)
    msg = Message(
        conversation_id=conversation_id,
        sequence_no=seq,
        role=role,
        content=content,
        **fields,
    )
    db.add(msg)
    await db.flush()
    return msg


async def _system_prompt(db: AsyncSession, project_id: uuid.UUID) -> str:
    instructions = await project_service.get_active_instructions(db, project_id)
    return instructions.content if instructions else ""


async def send_message(
    db: AsyncSession,
    conversation: Conversation,
    content: str,
    provider: str | None = None,
    model_id: str | None = None,
) -> tuple[Message, Message]:
    """Write-ahead send: persist the user message (committed) BEFORE calling the
    provider, then persist the assistant reply. If the adapter raises, the user
    message and all prior history remain intact and the error propagates."""
    provider = provider or DEFAULT_PROVIDER
    model_id = model_id or DEFAULT_MODEL

    # 1. Persist + commit the user message before any external call.
    user_msg = await _append(
        db, conversation.id, role="user", content=content, status="completed"
    )
    await db.commit()
    await db.refresh(user_msg)

    # 2. Build the canonical request from committed history.
    history = await list_messages(db, conversation.id)
    canonical = [
        CanonicalMessage(
            role=m.role,  # type: ignore[arg-type]
            content=m.content,
            source_provider=m.provider,
            source_model_id=m.model_id,
        )
        for m in history
        if m.role in ("user", "assistant")
    ]
    req = ProviderRequest(
        model_id=model_id,
        system_prompt=await _system_prompt(db, conversation.project_id),
        messages=canonical,
    )

    # 3. Call the adapter. On error this raises; history stays intact.
    adapter = get_adapter(provider)
    started = time.perf_counter()
    resp = await adapter.generate(req, api_key=None)
    latency_ms = int((time.perf_counter() - started) * 1000)

    # 4. Persist the assistant message and update the conversation's active model.
    assistant_msg = await _append(
        db,
        conversation.id,
        role="assistant",
        content=resp.content,
        provider=resp.provider,
        model_id=resp.model_id,
        status="completed",
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        total_tokens=resp.usage.total_tokens,
        latency_ms=latency_ms,
        provider_request_id=resp.provider_request_id,
    )
    conversation.active_provider = resp.provider
    conversation.active_model_id = resp.model_id
    await db.commit()
    await db.refresh(assistant_msg)
    return user_msg, assistant_msg
