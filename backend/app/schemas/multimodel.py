"""Multi-model (parallel / compare / synthesize) request & response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.conversation import MessageOut


class ModelTarget(BaseModel):
    provider: str
    model_id: str


class MultiSendIn(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    targets: list[ModelTarget] = Field(min_length=1, max_length=5)
    retry_message_id: uuid.UUID | None = None


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    user_message_id: uuid.UUID | None = None
    selected_message_id: uuid.UUID | None = None
    kind: str
    created_at: datetime


class MultiResponseError(BaseModel):
    category: str
    message: str
    retry_after_seconds: int | None = None


class MultiResponseOut(BaseModel):
    provider: str
    model_id: str
    message: MessageOut | None = None
    error: MultiResponseError | None = None


class MultiSendOut(BaseModel):
    group: GroupOut
    user_message: MessageOut
    responses: list[MultiResponseOut]


class GroupSelectIn(BaseModel):
    message_id: uuid.UUID


class CompareIn(BaseModel):
    target_provider: str
    target_model_id: str
    subject_message_id: uuid.UUID
    critique_focus: str | None = Field(default=None, max_length=500)


class SynthesizeIn(BaseModel):
    target_provider: str
    target_model_id: str
    source_message_ids: list[uuid.UUID] = Field(min_length=2, max_length=5)


class DerivedMessageOut(BaseModel):
    """A critique or synthesis result, with the group it may now continue."""

    message: MessageOut
    group: GroupOut | None = None
