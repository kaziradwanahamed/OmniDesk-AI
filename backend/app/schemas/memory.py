"""Project-memory request/response schemas: decisions and tasks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DecisionStatus = Literal["active", "superseded"]
TaskStatus = Literal["todo", "in_progress", "done", "blocked"]


# --------------------------------- Decisions ---------------------------------


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    rationale: str | None = None
    status: DecisionStatus = "active"
    source_message_id: uuid.UUID | None = None


class DecisionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    rationale: str | None = None
    status: DecisionStatus | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    rationale: str | None = None
    status: str
    source_message_id: uuid.UUID | None = None
    created_at: datetime


# ----------------------------------- Tasks -----------------------------------


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    details: str | None = None
    status: TaskStatus = "todo"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    details: str | None = None
    status: TaskStatus | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    details: str | None = None
    status: str
    is_active_task: bool
    updated_at: datetime
