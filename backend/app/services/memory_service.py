"""Persistent project memory: decisions and tasks CRUD + context lookups.

All reads/writes are scoped by ``project_id`` (ownership of the project is
enforced one layer up via ``require_project_owner``), so a decision or task is
only ever returned/mutated through the project that owns it — unowned or
cross-project ids resolve to ``None`` and the API maps that to 404.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectDecision, ProjectTask
from app.schemas.memory import (
    DecisionCreate,
    DecisionUpdate,
    TaskCreate,
    TaskUpdate,
)

# --------------------------------- Decisions ---------------------------------


async def list_decisions(
    db: AsyncSession, project_id: uuid.UUID
) -> list[ProjectDecision]:
    stmt = (
        select(ProjectDecision)
        .where(ProjectDecision.project_id == project_id)
        .order_by(ProjectDecision.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def list_active_decisions(
    db: AsyncSession, project_id: uuid.UUID
) -> list[ProjectDecision]:
    stmt = (
        select(ProjectDecision)
        .where(
            ProjectDecision.project_id == project_id,
            ProjectDecision.status == "active",
        )
        .order_by(ProjectDecision.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_decision(
    db: AsyncSession, project_id: uuid.UUID, decision_id: uuid.UUID
) -> ProjectDecision | None:
    stmt = select(ProjectDecision).where(
        ProjectDecision.id == decision_id,
        ProjectDecision.project_id == project_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_decision(
    db: AsyncSession, project_id: uuid.UUID, data: DecisionCreate
) -> ProjectDecision:
    decision = ProjectDecision(project_id=project_id, **data.model_dump())
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return decision


async def update_decision(
    db: AsyncSession, decision: ProjectDecision, data: DecisionUpdate
) -> ProjectDecision:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(decision, key, value)
    await db.commit()
    await db.refresh(decision)
    return decision


async def delete_decision(db: AsyncSession, decision: ProjectDecision) -> None:
    await db.delete(decision)
    await db.commit()


# ----------------------------------- Tasks -----------------------------------


async def list_tasks(db: AsyncSession, project_id: uuid.UUID) -> list[ProjectTask]:
    stmt = (
        select(ProjectTask)
        .where(ProjectTask.project_id == project_id)
        .order_by(ProjectTask.updated_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_active_task(
    db: AsyncSession, project_id: uuid.UUID
) -> ProjectTask | None:
    stmt = select(ProjectTask).where(
        ProjectTask.project_id == project_id,
        ProjectTask.is_active_task.is_(True),
    )
    return (await db.execute(stmt)).scalars().first()


async def get_task(
    db: AsyncSession, project_id: uuid.UUID, task_id: uuid.UUID
) -> ProjectTask | None:
    stmt = select(ProjectTask).where(
        ProjectTask.id == task_id,
        ProjectTask.project_id == project_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_task(
    db: AsyncSession, project_id: uuid.UUID, data: TaskCreate
) -> ProjectTask:
    task = ProjectTask(project_id=project_id, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession, task: ProjectTask, data: TaskUpdate
) -> ProjectTask:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: ProjectTask) -> None:
    await db.delete(task)
    await db.commit()


async def activate_task(
    db: AsyncSession, project_id: uuid.UUID, task: ProjectTask
) -> ProjectTask:
    """Mark exactly one task as the active focus (L3). Clears the flag on every
    other task in the project first, so there is always at most one active task."""
    await db.execute(
        update(ProjectTask)
        .where(
            ProjectTask.project_id == project_id,
            ProjectTask.id != task.id,
        )
        .values(is_active_task=False)
    )
    task.is_active_task = True
    await db.commit()
    await db.refresh(task)
    return task
