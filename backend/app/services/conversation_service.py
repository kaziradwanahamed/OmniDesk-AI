"""Conversation CRUD and the write-ahead message send pipeline (sync + streaming)."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import (
    NormalizedUsage,
    ProviderError,
    ProviderResponse,
)
from app.adapters.registry import get_adapter
from app.models.conversation import Conversation, Message
from app.services import (
    context_builder,
    provider_key_service,
    summarization_service,
    usage_service,
)

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


async def _resolve_target(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
    provider: str | None,
    model_id: str | None,
) -> tuple[str, str, str | None]:
    """Return (provider, model_id, api_key). Raises ProviderError on misconfig
    (before any message is persisted)."""
    provider = provider or conversation.active_provider or DEFAULT_PROVIDER
    if provider == "stub":
        return "stub", (model_id or DEFAULT_MODEL), None

    config = await provider_key_service.get_config(db, user_id, provider)
    api_key = await provider_key_service.resolve_key(db, user_id, provider, config)
    if not api_key:
        raise ProviderError(
            "AUTH_INVALID_KEY",
            f"No API key configured for {provider}. Add one in Provider Settings.",
        )
    enabled = list(config.enabled_models) if config else []
    model_id = model_id or conversation.active_model_id or (enabled[0] if enabled else None)
    if not model_id:
        raise ProviderError(
            "MODEL_UNAVAILABLE",
            "No model selected. Enable a model in Provider Settings.",
        )
    if enabled and model_id not in enabled:
        raise ProviderError(
            "MODEL_UNAVAILABLE", f"Model '{model_id}' is not enabled for {provider}."
        )
    return provider, model_id, api_key


async def _resolve_user_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    content: str,
    retry_message_id: uuid.UUID | None,
) -> Message:
    """Reuse the already-saved user row on a retry (no duplicate), otherwise
    write-ahead a fresh user message and commit it."""
    if retry_message_id is not None:
        existing = await db.get(Message, retry_message_id)
        if (
            existing is not None
            and existing.conversation_id == conversation_id
            and existing.role == "user"
        ):
            return existing
    msg = await _append(
        db, conversation_id, role="user", content=content, status="completed"
    )
    await db.commit()
    await db.refresh(msg)
    return msg


async def send_message(
    db: AsyncSession,
    conversation: Conversation,
    content: str,
    user_id: uuid.UUID,
    provider: str | None = None,
    model_id: str | None = None,
    retry_message_id: uuid.UUID | None = None,
) -> tuple[Message, Message]:
    """Non-streaming write-ahead send. Misconfig fails before persisting; provider
    errors after the user message is committed preserve history. On retry the
    prior user message is reused instead of duplicated."""
    provider, model_id, api_key = await _resolve_target(
        db, conversation, user_id, provider, model_id
    )

    user_msg = await _resolve_user_message(
        db, conversation.id, content, retry_message_id
    )

    built = await context_builder.build(
        db,
        conversation=conversation,
        target_provider=provider,
        target_model_id=model_id,
        user_message_content=content,
        exclude_message_id=user_msg.id,
        persist=True,
    )

    adapter = get_adapter(provider)
    started = time.perf_counter()
    resp = await adapter.generate(built.provider_request, api_key)
    latency_ms = int((time.perf_counter() - started) * 1000)

    assistant_msg = await _append(
        db,
        conversation.id,
        role="assistant",
        content=resp.content,
        provider=resp.provider,
        model_id=resp.model_id,
        status="completed",
        context_snapshot_id=built.snapshot_id,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        total_tokens=resp.usage.total_tokens,
        latency_ms=latency_ms,
        provider_request_id=resp.provider_request_id,
    )
    await usage_service.record(db, user_id, conversation, assistant_msg, resp)
    conversation.active_provider = resp.provider
    conversation.active_model_id = resp.model_id
    await db.commit()
    await db.refresh(assistant_msg)

    # Best-effort, opt-in rolling summary (never blocks or fails the chat turn).
    try:
        await summarization_service.maybe_auto_summarize(db, conversation, user_id)
    except Exception:  # noqa: BLE001 — summarization must never break a send
        pass
    return user_msg, assistant_msg


async def stream_message(
    db: AsyncSession,
    conversation: Conversation,
    content: str,
    user_id: uuid.UUID,
    provider: str | None = None,
    model_id: str | None = None,
    retry_message_id: uuid.UUID | None = None,
) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event_name, payload) for SSE. Write-ahead + history-preserving. On
    retry the prior user message is reused instead of duplicated."""
    try:
        provider, model_id, api_key = await _resolve_target(
            db, conversation, user_id, provider, model_id
        )
    except ProviderError as err:
        yield (
            "provider_error",
            {
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
            },
        )
        return

    user_msg = await _resolve_user_message(
        db, conversation.id, content, retry_message_id
    )
    yield (
        "user_message_saved",
        {"message_id": str(user_msg.id), "sequence_no": user_msg.sequence_no},
    )

    try:
        built = await context_builder.build(
            db,
            conversation=conversation,
            target_provider=provider,
            target_model_id=model_id,
            user_message_content=content,
            exclude_message_id=user_msg.id,
            persist=True,
        )
    except ProviderError as err:
        yield (
            "provider_error",
            {
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
                "retry_message_id": str(user_msg.id),
            },
        )
        return
    yield ("context_ready", built.snapshot_summary_dict())

    adapter = get_adapter(provider)
    accumulated: list[str] = []
    usage = NormalizedUsage()
    request_id: str | None = None
    finish_reason: str | None = None
    started = time.perf_counter()
    try:
        async for chunk in adapter.stream(built.provider_request, api_key):
            if chunk.delta_text:
                accumulated.append(chunk.delta_text)
                yield ("delta", {"text": chunk.delta_text})
            if chunk.is_final:
                usage = chunk.usage or NormalizedUsage()
                request_id = chunk.provider_request_id
                finish_reason = chunk.finish_reason
    except ProviderError as err:
        yield (
            "provider_error",
            {
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
                "retry_message_id": str(user_msg.id),
            },
        )
        return

    latency_ms = int((time.perf_counter() - started) * 1000)
    text = "".join(accumulated)
    assistant_msg = await _append(
        db,
        conversation.id,
        role="assistant",
        content=text,
        provider=provider,
        model_id=model_id,
        status="completed",
        context_snapshot_id=built.snapshot_id,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        latency_ms=latency_ms,
        provider_request_id=request_id,
    )
    await usage_service.record(
        db,
        user_id,
        conversation,
        assistant_msg,
        ProviderResponse(
            provider=provider,
            model_id=model_id,
            content=text,
            usage=usage,
            provider_request_id=request_id,
            finish_reason=finish_reason,
        ),
    )
    conversation.active_provider = provider
    conversation.active_model_id = model_id
    await db.commit()
    await db.refresh(assistant_msg)
    yield (
        "message_complete",
        {
            "message_id": str(assistant_msg.id),
            "sequence_no": assistant_msg.sequence_no,
            "provider": provider,
            "model_id": model_id,
            "content": text,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
            },
            "latency_ms": latency_ms,
            "provider_request_id": request_id,
        },
    )


async def switch_model(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
    provider: str,
    model_id: str,
) -> tuple[Conversation, Message | None]:
    """Seamless manual model switch within one conversation.

    Validates the target is configured/enabled (raising ProviderError otherwise —
    never a silent switch), then updates ``active_provider``/``active_model_id``
    in place and records a ``system_event`` divider row. The conversation is
    never recreated and no history is touched. Returns the updated conversation
    and the divider row (``None`` when the target already matched the active
    model, i.e. a no-op)."""
    resolved_provider, resolved_model, _ = await _resolve_target(
        db, conversation, user_id, provider, model_id
    )

    old_provider = conversation.active_provider
    old_model = conversation.active_model_id
    if old_provider == resolved_provider and old_model == resolved_model:
        return conversation, None

    event = await _append(
        db,
        conversation.id,
        role="system_event",
        content=(
            f"Continuing this conversation with {resolved_provider} "
            f"({resolved_model}) using the shared project context."
        ),
        provider=resolved_provider,
        model_id=resolved_model,
        metadata_json={
            "event": "model_switched",
            "from": {"provider": old_provider, "model_id": old_model},
            "to": {"provider": resolved_provider, "model_id": resolved_model},
        },
    )
    conversation.active_provider = resolved_provider
    conversation.active_model_id = resolved_model
    await db.commit()
    await db.refresh(event)
    await db.refresh(conversation)
    return conversation, event
