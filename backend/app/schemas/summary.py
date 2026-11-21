"""Conversation-summary request/response schemas (L6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    version: int
    covers_up_to_sequence: int
    covered_message_count: int
    content: str
    estimated_tokens: int
    provider: str | None = None
    model_id: str | None = None
    user_edited: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SummaryStatusOut(BaseModel):
    """Active summary (if any) plus the threshold indicator for the UI."""

    summary: SummaryOut | None = None
    unsummarized_count: int
    trigger_threshold: int
    needs_summary: bool


class SummaryRefreshIn(BaseModel):
    # Optional override; defaults to the conversation's active provider/model.
    provider: str | None = None
    model_id: str | None = None


class SummaryUpdateIn(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
