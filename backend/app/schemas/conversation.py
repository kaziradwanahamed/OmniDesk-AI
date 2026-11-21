"""Conversation and message request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    active_provider: str | None = None
    active_model_id: str | None = None
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sequence_no: int
    role: str
    content: str
    provider: str | None = None
    model_id: str | None = None
    status: str
    error_code: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    provider_request_id: str | None = None
    created_at: datetime


class MessageSendIn(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    provider: str | None = None
    model_id: str | None = None


class MessageSendOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
