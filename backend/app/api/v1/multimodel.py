"""Multi-model endpoints: parallel send, group selection, compare, synthesize.

All routes are owner-enforced (404 for missing/unowned conversations, groups, or
messages — no existence leak). Provider failures on compare/synthesize return 502
with a categorized error; the parallel send isolates per-provider failures inside
the response list so successful peers are always returned.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderError
from app.api.deps import get_current_user, require_conversation_owner, require_csrf
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.message_group import MessageGroup
from app.models.project import Project
from app.models.user import User
from app.schemas.conversation import MessageOut
from app.schemas.multimodel import (
    CompareIn,
    DerivedMessageOut,
    GroupOut,
    GroupSelectIn,
    MultiResponseError,
    MultiResponseOut,
    MultiSendIn,
    MultiSendOut,
    SynthesizeIn,
)
from app.services import comparison_service, multimodel_service

router = APIRouter(tags=["multimodel"])


async def _owned_message(
    db: AsyncSession, conversation: Conversation, message_id: uuid.UUID
) -> Message:
    msg = await db.get(Message, message_id)
    if msg is None or msg.conversation_id != conversation.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")
    return msg


def _response_dto(r: dict) -> MultiResponseOut:
    err = r.get("error")
    return MultiResponseOut(
        provider=r["provider"],
        model_id=r["model_id"],
        message=MessageOut.model_validate(r["message"]) if r.get("message") else None,
        error=(
            MultiResponseError(
                category=err.category,
                message=err.user_message,
                retry_after_seconds=err.retry_after_seconds,
            )
            if err is not None
            else None
        ),
    )


@router.post(
    "/conversations/{conversation_id}/messages/multi",
    response_model=MultiSendOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def multi_send(
    data: MultiSendIn,
    conversation: Conversation = Depends(require_conversation_owner),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    targets = [(t.provider, t.model_id) for t in data.targets]
    group, user_msg, responses = await multimodel_service.multi_send(
        db, conversation, data.content, user.id, targets, data.retry_message_id
    )
    return MultiSendOut(
        group=GroupOut.model_validate(group),
        user_message=MessageOut.model_validate(user_msg),
        responses=[_response_dto(r) for r in responses],
    )


@router.get(
    "/conversations/{conversation_id}/message-groups",
    response_model=list[GroupOut],
)
async def list_message_groups(
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MessageGroup)
        .where(MessageGroup.conversation_id == conversation.id)
        .order_by(MessageGroup.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.patch(
    "/message-groups/{group_id}/select",
    response_model=GroupOut,
    dependencies=[Depends(require_csrf)],
)
async def select_group_message(
    group_id: uuid.UUID,
    data: GroupSelectIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MessageGroup)
        .join(Conversation, MessageGroup.conversation_id == Conversation.id)
        .join(Project, Conversation.project_id == Project.id)
        .where(MessageGroup.id == group_id, Project.user_id == user.id)
    )
    group = (await db.execute(stmt)).scalar_one_or_none()
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message group not found")
    message = await db.get(Message, data.message_id)
    if message is None or message.group_id != group.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not in this group")
    return await multimodel_service.select_group_message(db, group, message)


@router.post(
    "/conversations/{conversation_id}/compare",
    response_model=DerivedMessageOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def compare(
    data: CompareIn,
    conversation: Conversation = Depends(require_conversation_owner),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await _owned_message(db, conversation, data.subject_message_id)
    try:
        message, group = await comparison_service.compare(
            db, conversation, user.id, data.target_provider, data.target_model_id,
            subject, data.critique_focus,
        )
    except ProviderError as err:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
            },
        )
    return DerivedMessageOut(
        message=MessageOut.model_validate(message),
        group=GroupOut.model_validate(group) if group is not None else None,
    )


@router.post(
    "/conversations/{conversation_id}/synthesize",
    response_model=DerivedMessageOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def synthesize(
    data: SynthesizeIn,
    conversation: Conversation = Depends(require_conversation_owner),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sources = [await _owned_message(db, conversation, mid) for mid in data.source_message_ids]
    try:
        message, group = await comparison_service.synthesize(
            db, conversation, user.id, data.target_provider, data.target_model_id, sources
        )
    except ProviderError as err:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
            },
        )
    return DerivedMessageOut(
        message=MessageOut.model_validate(message),
        group=GroupOut.model_validate(group) if group is not None else None,
    )
