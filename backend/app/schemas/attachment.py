"""Project file (attachment) request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    extraction_status: str
    extraction_error: str | None = None
    chunk_count: int
    pinned: bool
    created_at: datetime
    updated_at: datetime


class AttachmentUploadOut(AttachmentOut):
    # True when an identical file (same SHA-256) already existed in the project
    # and was returned instead of creating a duplicate.
    deduplicated: bool = False


class AttachmentUpdate(BaseModel):
    pinned: bool | None = None
    filename: str | None = Field(default=None, min_length=1, max_length=255)


class AttachmentChunkOut(BaseModel):
    """One stored excerpt of an owned file (for inspecting extraction output)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    content: str
    token_est: int
    char_start: int
    char_end: int
    start_line: int | None = None
    end_line: int | None = None
    page_start: int | None = None
    page_end: int | None = None


class FileExcerptOut(BaseModel):
    """One Layer-5 excerpt surfaced in the Context Inspector (no file body)."""

    filename: str
    chunk_index: int
    token_est: int
    pinned: bool
    matched: bool
    rank: float | None = None
