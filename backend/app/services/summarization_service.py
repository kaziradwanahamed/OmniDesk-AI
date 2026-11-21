"""Rolling conversation summarization (Blueprint Ch. 19, context layer L6).

Compacts older messages into a structured, versioned summary so long
conversations stay within budget. A summary is an auditable convenience layer:
the canonical ``messages`` rows are NEVER deleted or mutated. At most one summary
is active per conversation; editing or re-summarizing supersedes it with a new
version (a partial unique index enforces the single-active invariant).

To avoid an import cycle (context_builder imports this module for L6), provider
resolution is done locally rather than importing conversation_service.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import CanonicalMessage, ProviderError, ProviderRequest
from app.adapters.registry import get_adapter
from app.core.config import get_settings
from app.models.context_summary import ConversationSummary
from app.models.conversation import Conversation, Message
from app.services import provider_key_service
from app.services.token_estimate import estimate_tokens

SUMMARY_SYSTEM = (
    "You are a summarization engine for OmniDesk AI, a multi-model project "
    "workspace. Compress the older part of a project conversation into a compact, "
    "information-dense rolling summary that a different AI model can safely rely on "
    "as established context. Preserve exactly: key decisions and constraints, file "
    "names and code symbols, unfinished tasks, and open questions. Do not invent "
    "facts. If an existing rolling summary is provided, update it by folding in the "
    "new messages without dropping still-relevant prior facts. Output EXACTLY these "
    "five sections, each under its own header:\n"
    "1. Completed Work\n"
    "2. Established Decisions & Constraints\n"
    "3. Key Files & Code Symbols\n"
    "4. Unresolved Issues & Next Steps\n"
    "5. Open Questions\n"
    "Be concise; omit a section's bullets only if genuinely empty."
)


async def get_active_summary(
    db: AsyncSession, conversation_id: uuid.UUID
) -> ConversationSummary | None:
    stmt = select(ConversationSummary).where(
        ConversationSummary.conversation_id == conversation_id,
        ConversationSummary.is_active.is_(True),
    )
    return (await db.execute(stmt)).scalars().first()


async def _load_messages(
    db: AsyncSession, conversation_id: uuid.UUID
) -> list[Message]:
    stmt = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.role.in_(("user", "assistant")),
        )
        .order_by(Message.sequence_no.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def unsummarized_count(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    active_summary: ConversationSummary | None,
) -> int:
    covers = active_summary.covers_up_to_sequence if active_summary else 0
    stmt = (
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.role.in_(("user", "assistant")),
            Message.sequence_no > covers,
        )
    )
    return int(await db.scalar(stmt) or 0)


async def should_summarize(db: AsyncSession, conversation: Conversation) -> bool:
    active = await get_active_summary(db, conversation.id)
    count = await unsummarized_count(db, conversation.id, active)
    return count > get_settings().summary_trigger_message_count


async def _resolve(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
    provider: str | None,
    model_id: str | None,
) -> tuple[str, str, str | None]:
    """Resolve (provider, model_id, api_key) for the summarizer call. Mirrors the
    conversation send resolution (kept local to avoid an import cycle)."""
    provider = provider or conversation.active_provider or "stub"
    if provider == "stub":
        return "stub", (model_id or "stub-echo"), None
    config = await provider_key_service.get_config(db, user_id, provider)
    api_key = await provider_key_service.resolve_key(db, user_id, provider, config)
    if not api_key:
        raise ProviderError(
            "AUTH_INVALID_KEY",
            f"No API key configured for {provider}; cannot summarize.",
        )
    enabled = list(config.enabled_models) if config else []
    model_id = model_id or conversation.active_model_id or (enabled[0] if enabled else None)
    if not model_id:
        raise ProviderError("MODEL_UNAVAILABLE", "No model selected for summarization.")
    if enabled and model_id not in enabled:
        raise ProviderError(
            "MODEL_UNAVAILABLE", f"Model '{model_id}' is not enabled for {provider}."
        )
    return provider, model_id, api_key


def _format_message(m: Message) -> str:
    if m.role == "user":
        return f"USER: {m.content}"
    tag = f"{m.provider or '?'}/{m.model_id or '?'}"
    return f"ASSISTANT ({tag}): {m.content}"


def _build_request(
    prior: ConversationSummary | None,
    messages: list[Message],
    model_id: str,
    max_tokens: int,
) -> ProviderRequest:
    parts: list[str] = []
    if prior is not None and prior.content:
        parts.append(
            f"EXISTING ROLLING SUMMARY (version {prior.version}):\n{prior.content}\n"
        )
    parts.append("NEW MESSAGES TO FOLD INTO THE SUMMARY (oldest first):")
    parts.extend(_format_message(m) for m in messages)
    return ProviderRequest(
        model_id=model_id,
        system_prompt=SUMMARY_SYSTEM,
        messages=[CanonicalMessage(role="user", content="\n".join(parts))],
        max_output_tokens=max_tokens,
    )


async def _store_new_version(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    content: str,
    covers_up_to: int,
    covered_count: int,
    provider: str | None,
    model_id: str | None,
    user_edited: bool,
    prior: ConversationSummary | None,
) -> ConversationSummary:
    next_version = (prior.version + 1) if prior else 1
    if prior is not None:
        prior.is_active = False
        await db.flush()  # satisfy the partial unique index before inserting
    row = ConversationSummary(
        conversation_id=conversation_id,
        version=next_version,
        covers_up_to_sequence=covers_up_to,
        covered_message_count=covered_count,
        content=content,
        estimated_tokens=estimate_tokens(content),
        provider=provider,
        model_id=model_id,
        user_edited=user_edited,
        is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def summarize(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
    provider: str | None = None,
    model_id: str | None = None,
) -> ConversationSummary | None:
    """Generate/refresh the rolling summary using the conversation's configured
    provider. Folds the prior summary + newly-aged messages into a new version,
    keeping the most-recent tail unsummarized. Returns None when there is nothing
    old enough to summarize. Raises ProviderError on a provider failure (callers
    handle it without losing existing state). Canonical rows are never touched."""
    settings = get_settings()
    tail = settings.summary_recent_tail_messages
    messages = await _load_messages(db, conversation.id)
    if len(messages) <= tail:
        return await get_active_summary(db, conversation.id)  # nothing to compact yet

    prior = await get_active_summary(db, conversation.id)
    prior_covers = prior.covers_up_to_sequence if prior else 0

    to_cover = messages[: len(messages) - tail]
    new_covers_up_to = to_cover[-1].sequence_no
    if prior is not None and new_covers_up_to <= prior_covers:
        return prior  # already covered; nothing newly aged

    newly_aged = [m for m in to_cover if m.sequence_no > prior_covers]
    source = newly_aged or to_cover

    resolved_provider, resolved_model, api_key = await _resolve(
        db, conversation, user_id, provider, model_id
    )
    req = _build_request(prior, source, resolved_model, settings.summary_max_output_tokens)
    adapter = get_adapter(resolved_provider)
    resp = await adapter.generate(req, api_key)  # may raise ProviderError

    covered_count = sum(1 for m in messages if m.sequence_no <= new_covers_up_to)
    return await _store_new_version(
        db,
        conversation.id,
        content=resp.content.strip(),
        covers_up_to=new_covers_up_to,
        covered_count=covered_count,
        provider=resolved_provider,
        model_id=resolved_model,
        user_edited=False,
        prior=prior,
    )


async def update_summary(
    db: AsyncSession, conversation: Conversation, content: str
) -> ConversationSummary:
    """Persist a user correction as a new active version (user_edited=True)."""
    prior = await get_active_summary(db, conversation.id)
    if prior is not None:
        return await _store_new_version(
            db,
            conversation.id,
            content=content.strip(),
            covers_up_to=prior.covers_up_to_sequence,
            covered_count=prior.covered_message_count,
            provider=prior.provider,
            model_id=prior.model_id,
            user_edited=True,
            prior=prior,
        )
    # No prior summary: author a v1 covering everything but the recent tail.
    tail = get_settings().summary_recent_tail_messages
    messages = await _load_messages(db, conversation.id)
    if len(messages) > tail:
        covers = messages[len(messages) - tail - 1].sequence_no
    elif messages:
        covers = messages[-1].sequence_no
    else:
        covers = 0
    covered_count = sum(1 for m in messages if m.sequence_no <= covers)
    return await _store_new_version(
        db,
        conversation.id,
        content=content.strip(),
        covers_up_to=covers,
        covered_count=covered_count,
        provider=None,
        model_id=None,
        user_edited=True,
        prior=None,
    )


async def clear_summary(db: AsyncSession, conversation: Conversation) -> None:
    """Deactivate the active summary. Canonical messages are never affected;
    the superseded row is kept for audit, just no longer active."""
    prior = await get_active_summary(db, conversation.id)
    if prior is not None:
        prior.is_active = False
        await db.commit()


async def maybe_auto_summarize(
    db: AsyncSession, conversation: Conversation, user_id: uuid.UUID
) -> ConversationSummary | None:
    """Best-effort post-turn summarization. Opt-in (``summary_auto_enabled``) and
    non-blocking: any provider error is swallowed so the chat turn is unaffected."""
    if not get_settings().summary_auto_enabled:
        return None
    if not await should_summarize(db, conversation):
        return None
    try:
        return await summarize(db, conversation, user_id)
    except ProviderError:
        return None
