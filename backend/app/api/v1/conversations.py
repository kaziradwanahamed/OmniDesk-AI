"""Conversation detail endpoints and message list/send (owner-enforced)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderError
from app.api.deps import require_conversation_owner, require_csrf
from app.db.session import get_db
from app.models.conversation import Conversation
from app.schemas.conversation import (
    ConversationOut,
    ConversationRename,
    MessageOut,
    MessageSendIn,
    MessageSendOut,
)
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation: Conversation = Depends(require_conversation_owner),
) -> Conversation:
    return conversation


@router.patch(
    "/{conversation_id}",
    response_model=ConversationOut,
    dependencies=[Depends(require_csrf)],
)
async def rename_conversation(
    data: ConversationRename,
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    return await conversation_service.rename_conversation(db, conversation, data.title)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_conversation(
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    await conversation_service.delete_conversation(db, conversation)
    return None


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
):
    return await conversation_service.list_messages(db, conversation.id)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageSendOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def send_message(
    data: MessageSendIn,
    conversation: Conversation = Depends(require_conversation_owner),
    db: AsyncSession = Depends(get_db),
):
    try:
        user_msg, assistant_msg = await conversation_service.send_message(
            db, conversation, data.content, data.provider, data.model_id
        )
    except ProviderError as err:
        # The user message + prior history are already committed and intact.
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "category": err.category,
                "message": err.user_message,
                "retry_after_seconds": err.retry_after_seconds,
            },
        )
    return MessageSendOut(
        user_message=MessageOut.model_validate(user_msg),
        assistant_message=MessageOut.model_validate(assistant_msg),
    )
