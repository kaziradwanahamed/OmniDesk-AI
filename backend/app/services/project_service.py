"""Project and project-instructions domain logic."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectInstruction
from app.schemas.project import InstructionsUpdate, ProjectCreate, ProjectUpdate


async def list_projects(db: AsyncSession, user_id: uuid.UUID) -> list[Project]:
    stmt = (
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.updated_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_project(
    db: AsyncSession, user_id: uuid.UUID, data: ProjectCreate
) -> Project:
    project = Project(user_id=user_id, **data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession, project: Project, data: ProjectUpdate
) -> Project:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()


async def get_active_instructions(
    db: AsyncSession, project_id: uuid.UUID
) -> ProjectInstruction | None:
    stmt = (
        select(ProjectInstruction)
        .where(
            ProjectInstruction.project_id == project_id,
            ProjectInstruction.is_active.is_(True),
        )
        .order_by(ProjectInstruction.version.desc())
    )
    return (await db.execute(stmt)).scalars().first()


async def update_instructions(
    db: AsyncSession, project_id: uuid.UUID, data: InstructionsUpdate
) -> ProjectInstruction:
    """Create a new active instruction version; deactivate the previous one.

    A partial unique index allows only one active row per project, so the
    deactivation is flushed before inserting the new active row.
    """
    current = await get_active_instructions(db, project_id)
    next_version = (current.version + 1) if current else 1
    if current is not None:
        current.is_active = False
        await db.flush()

    new_row = ProjectInstruction(
        project_id=project_id,
        content=data.content,
        response_style=data.response_style,
        version=next_version,
        is_active=True,
    )
    db.add(new_row)
    await db.commit()
    await db.refresh(new_row)
    return new_row
