"""Conversation summary (L6) endpoints: inspect, refresh, edit, clear.

All routes are owner-enforced via ``require_conversation_owner`` (404 for
missing/unowned conversations — no existence leak). Summarization reuses the
conversation's configured provider and never silently switches; a provider
failure returns 502 with the existing summary and history fully intact.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderError
from app.api.deps import get_current_user, require_conversation_owner, require_csrf
from app.core.config import get_settings
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.summary import (
    SummaryOut,
    SummaryRefreshIn,
    SummaryStatusOut,
    SummaryUpdateIn,
)
from app.services import summarization_service

router = APIRouter(prefix="/conversations", tags=["summaries"])


@router.get("/{conversation_id}/summary", response_model=SummaryStatusOut)
async def get_summary(
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
):
    active = await summarization_service.get_active_summary(db, conversation.id)
    count = await summarization_service.unsummarized_count(db, conversation.id, active)
    threshold = get_settings().summary_trigger_message_count
    return SummaryStatusOut(
        summary=SummaryOut.model_validate(active) if active else None,
        unsummarized_count=count,
        trigger_threshold=threshold,
        needs_summary=count > threshold,
    )


@router.post(
    "/{conversation_id}/summary/refresh",
    response_model=SummaryStatusOut,
    dependencies=[Depends(require_csrf)],
)
async def refresh_summary(
    data: SummaryRefreshIn,
    conversation: Conversation = Depends(require_conversation_owner),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await summarization_service.summarize(
            db, conversation, user.id, data.provider, data.model_id
        )
    except ProviderError as err:
        # Non-blocking: the existing summary + history are untouched.
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
            },
        )
    active = await summarization_service.get_active_summary(db, conversation.id)
    count = await summarization_service.unsummarized_count(db, conversation.id, active)
    threshold = get_settings().summary_trigger_message_count
    return SummaryStatusOut(
        summary=SummaryOut.model_validate(active) if active else None,
        unsummarized_count=count,
        trigger_threshold=threshold,
        needs_summary=count > threshold,
    )


@router.put(
    "/{conversation_id}/summary",
    response_model=SummaryOut,
    dependencies=[Depends(require_csrf)],
)
async def edit_summary(
    data: SummaryUpdateIn,
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
):
    return await summarization_service.update_summary(db, conversation, data.content)


@router.delete(
    "/{conversation_id}/summary",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def clear_summary(
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    await summarization_service.clear_summary(db, conversation)
    return None
