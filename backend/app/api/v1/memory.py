"""Persistent project-memory endpoints: decisions and tasks (owner-enforced).

Ownership is enforced by ``require_project_owner`` (404 for missing/unowned
projects). Nested decision/task ids are resolved *within* the owned project, so a
cross-project id returns 404 — never another user's memory.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_csrf, require_project_owner
from app.db.session import get_db
from app.models.project import Project
from app.schemas.memory import (
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.services import memory_service

router = APIRouter(prefix="/projects", tags=["memory"])


# --------------------------------- Decisions ---------------------------------


@router.get("/{project_id}/decisions", response_model=list[DecisionOut])
async def list_decisions(
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.list_decisions(db, project.id)


@router.post(
    "/{project_id}/decisions",
    response_model=DecisionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_decision(
    data: DecisionCreate,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.create_decision(db, project.id, data)


@router.patch(
    "/{project_id}/decisions/{decision_id}",
    response_model=DecisionOut,
    dependencies=[Depends(require_csrf)],
)
async def update_decision(
    decision_id: uuid.UUID,
    data: DecisionUpdate,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    decision = await memory_service.get_decision(db, project.id, decision_id)
    if decision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")
    return await memory_service.update_decision(db, decision, data)


@router.delete(
    "/{project_id}/decisions/{decision_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_decision(
    decision_id: uuid.UUID,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    decision = await memory_service.get_decision(db, project.id, decision_id)
    if decision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")
    await memory_service.delete_decision(db, decision)
    return None


# ----------------------------------- Tasks -----------------------------------


@router.get("/{project_id}/tasks", response_model=list[TaskOut])
async def list_tasks(
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.list_tasks(db, project.id)


@router.post(
    "/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_task(
    data: TaskCreate,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.create_task(db, project.id, data)


@router.patch(
    "/{project_id}/tasks/{task_id}",
    response_model=TaskOut,
    dependencies=[Depends(require_csrf)],
)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    task = await memory_service.get_task(db, project.id, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return await memory_service.update_task(db, task, data)


@router.patch(
    "/{project_id}/tasks/{task_id}/activate",
    response_model=TaskOut,
    dependencies=[Depends(require_csrf)],
)
async def activate_task(
    task_id: uuid.UUID,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    task = await memory_service.get_task(db, project.id, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return await memory_service.activate_task(db, project.id, task)


@router.delete(
    "/{project_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_task(
    task_id: uuid.UUID,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await memory_service.get_task(db, project.id, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    await memory_service.delete_task(db, task)
    return None
