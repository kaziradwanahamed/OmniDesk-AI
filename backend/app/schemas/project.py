"""Project and instructions request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["active", "paused", "archived"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    goals: str | None = None
    tech_stack: str | None = None
    status: ProjectStatus = "active"
    progress_notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    goals: str | None = None
    tech_stack: str | None = None
    status: ProjectStatus | None = None
    progress_notes: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    goals: str | None = None
    tech_stack: str | None = None
    status: str
    progress_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class InstructionsUpdate(BaseModel):
    content: str = Field(min_length=1)
    response_style: str | None = None


class InstructionsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    response_style: str | None = None
    version: int
    is_active: bool
    updated_at: datetime
