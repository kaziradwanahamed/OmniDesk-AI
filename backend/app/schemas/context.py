"""Context-inspector and model-switch request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.conversation import ConversationOut, MessageOut


class ContextSnapshotOut(BaseModel):
    """A persisted, historical audit of the context sent on a completed turn."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    target_provider: str
    target_model_id: str
    token_budget: int
    estimated_input_tokens: int
    included_layers: list[str]
    omitted_items: list[dict]
    created_at: datetime


class ContextPreviewOut(BaseModel):
    """A dry-run of the ContextBuilder for the *next* turn (nothing persisted)."""

    target_provider: str
    target_model_id: str
    token_budget: int
    estimated_input_tokens: int
    included_layers: list[str]
    # Per-layer estimated token counts (e.g. {"summary:v2": 410, "recent_messages:6": 820}).
    layer_tokens: dict[str, int]
    omitted_items: list[dict]
    recent_message_count: int
    system_prompt: str


class ModelSwitchIn(BaseModel):
    provider: str
    model_id: str


class ModelSwitchOut(BaseModel):
    conversation: ConversationOut
    # The system_event divider row, when the switch actually changed the model.
    event: MessageOut | None = None
