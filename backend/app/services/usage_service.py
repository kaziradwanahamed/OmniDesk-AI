"""Usage ledger: record verified provider token usage and aggregate it."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderResponse
from app.models.conversation import Conversation, Message
from app.models.provider_config import UsageRecord


async def record(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation: Conversation,
    message: Message,
    response: ProviderResponse,
) -> UsageRecord | None:
    """Persist a usage row only when the provider actually returned token counts.
    Never fabricates numbers. Caller commits."""
    u = response.usage
    if u.input_tokens is None and u.output_tokens is None and u.total_tokens is None:
        return None
    rec = UsageRecord(
        user_id=user_id,
        project_id=conversation.project_id,
        conversation_id=conversation.id,
        message_id=message.id,
        provider=response.provider,
        model_id=response.model_id,
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        total_tokens=u.total_tokens,
        provider_request_id=response.provider_request_id,
    )
    db.add(rec)
    return rec


async def summary(db: AsyncSession, user_id: uuid.UUID) -> dict:
    stmt = (
        select(
            UsageRecord.provider,
            UsageRecord.model_id,
            func.coalesce(func.sum(UsageRecord.input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.count(),
        )
        .where(UsageRecord.user_id == user_id)
        .group_by(UsageRecord.provider, UsageRecord.model_id)
        .order_by(func.coalesce(func.sum(UsageRecord.total_tokens), 0).desc())
    )
    rows = (await db.execute(stmt)).all()
    by_model = [
        {
            "provider": r[0],
            "model_id": r[1],
            "input_tokens": int(r[2]),
            "output_tokens": int(r[3]),
            "total_tokens": int(r[4]),
            "request_count": int(r[5]),
        }
        for r in rows
    ]
    return {
        "input_tokens": sum(m["input_tokens"] for m in by_model),
        "output_tokens": sum(m["output_tokens"] for m in by_model),
        "total_tokens": sum(m["total_tokens"] for m in by_model),
        "by_model": by_model,
    }
