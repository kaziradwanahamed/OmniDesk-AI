"""Project CRUD and project-instructions endpoints (owner-enforced)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_csrf, require_project_owner
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    InstructionsOut,
    InstructionsUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Project]:
    return await project_service.list_projects(db, user.id)


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    return await project_service.create_project(db, user.id, data)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project: Project = Depends(require_project_owner)) -> Project:
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectOut,
    dependencies=[Depends(require_csrf)],
)
async def update_project(
    data: ProjectUpdate,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
) -> Project:
    return await project_service.update_project(db, project, data)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_project(
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    await project_service.delete_project(db, project)
    return None


@router.get("/{project_id}/instructions", response_model=InstructionsOut | None)
async def get_instructions(
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    return await project_service.get_active_instructions(db, project.id)


@router.put(
    "/{project_id}/instructions",
    response_model=InstructionsOut,
    dependencies=[Depends(require_csrf)],
)
async def put_instructions(
    data: InstructionsUpdate,
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    return await project_service.update_instructions(db, project.id, data)
