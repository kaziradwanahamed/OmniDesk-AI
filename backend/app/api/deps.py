"""Shared FastAPI dependencies: current user, CSRF guard, project ownership."""

from __future__ import annotations

import secrets
import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.user import User


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get(security.ACCESS_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        payload = security.decode_access_token(token)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user


async def require_csrf(request: Request) -> None:
    """Double-submit CSRF guard for state-changing requests."""
    cookie = request.cookies.get(security.CSRF_COOKIE)
    header = request.headers.get("X-CSRF-Token")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed"
        )


async def require_project_owner(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """Load a project and enforce ownership. Returns 404 for missing OR unowned
    projects (never 403) to avoid leaking resource existence."""
    project = await db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project


async def require_conversation_owner(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    """Load a conversation and enforce ownership via its parent project. Returns
    404 for missing OR unowned conversations."""
    stmt = (
        select(Conversation)
        .join(Project, Conversation.project_id == Project.id)
        .where(Conversation.id == conversation_id, Project.user_id == user.id)
    )
    conversation = (await db.execute(stmt)).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return conversation
