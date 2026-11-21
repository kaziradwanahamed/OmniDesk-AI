"""Context transparency + seamless model switching endpoints.

- GET  /conversations/{cid}/context-preview  — dry-run the ContextBuilder for the
  next turn (nothing persisted) so the "Context Included" inspector can show
  exactly which layers and how many estimated tokens would be sent.
- PATCH /conversations/{cid}/model           — switch the active provider/model in
  place (records a system_event divider; never recreates the conversation).
- GET  /context-snapshots/{sid}              — inspect the persisted audit of the
  context sent on a historical completed turn.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderError
from app.api.deps import (
    get_current_user,
    require_conversation_owner,
    require_csrf,
)
from app.db.session import get_db
from app.models.context_snapshot import ContextSnapshot
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.user import User
from app.schemas.context import (
    ContextPreviewOut,
    ContextSnapshotOut,
    ModelSwitchIn,
    ModelSwitchOut,
)
from app.schemas.conversation import ConversationOut, MessageOut
from app.services import context_builder, conversation_service

router = APIRouter(tags=["context"])

_DEFAULT_PROVIDER = conversation_service.DEFAULT_PROVIDER
_DEFAULT_MODEL = conversation_service.DEFAULT_MODEL


@router.get(
    "/conversations/{conversation_id}/context-preview",
    response_model=ContextPreviewOut,
)
async def context_preview(
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
):
    provider = conversation.active_provider or _DEFAULT_PROVIDER
    model_id = conversation.active_model_id or _DEFAULT_MODEL
    built = await context_builder.build(
        db,
        conversation=conversation,
        target_provider=provider,
        target_model_id=model_id,
        user_message_content="",  # dry run: no pending message yet
        persist=False,
    )
    return ContextPreviewOut(
        target_provider=provider,
        target_model_id=model_id,
        token_budget=built.token_budget,
        estimated_input_tokens=built.estimated_input_tokens,
        included_layers=built.included_layers,
        omitted_items=built.omitted_items,
        recent_message_count=built.recent_message_count,
        system_prompt=built.system_prompt,
    )


@router.patch(
    "/conversations/{conversation_id}/model",
    response_model=ModelSwitchOut,
    dependencies=[Depends(require_csrf)],
)
async def switch_model(
    data: ModelSwitchIn,
    conversation: Conversation = Depends(require_conversation_owner),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        updated, event = await conversation_service.switch_model(
            db, conversation, user.id, data.provider, data.model_id
        )
    except ProviderError as err:
        # Pre-flight validation failure (missing key / model not enabled). The
        # conversation is unchanged; the client keeps its draft and history.
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
            },
        )
    return ModelSwitchOut(
        conversation=ConversationOut.model_validate(updated),
        event=MessageOut.model_validate(event) if event is not None else None,
    )


@router.get(
    "/context-snapshots/{snapshot_id}",
    response_model=ContextSnapshotOut,
)
async def get_context_snapshot(
    snapshot_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ContextSnapshot)
        .join(Conversation, ContextSnapshot.conversation_id == Conversation.id)
        .join(Project, Conversation.project_id == Project.id)
        .where(
            ContextSnapshot.id == snapshot_id,
            Project.user_id == user.id,
        )
    )
    snapshot = (await db.execute(stmt)).scalar_one_or_none()
    if snapshot is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Context snapshot not found"},
        )
    return snapshot
