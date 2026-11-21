"""Authentication endpoints: register, login, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core import security
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_session(response: Response, user: User) -> None:
    access = security.create_access_token(str(user.id))
    csrf = security.new_csrf_token()
    security.set_auth_cookies(response, access, csrf)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterIn, response: Response, db: AsyncSession = Depends(get_db)
) -> User:
    try:
        user = await auth_service.create_user(
            db, data.email, data.password, data.display_name
        )
    except auth_service.EmailAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    _issue_session(response, user)
    return user


@router.post("/login", response_model=UserOut)
async def login(
    data: LoginIn, response: Response, db: AsyncSession = Depends(get_db)
) -> User:
    user = await auth_service.authenticate(db, data.email, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    _issue_session(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    security.clear_auth_cookies(response)
    return None


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
