"""Authentication domain logic: user creation and credential verification."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User


class EmailAlreadyExists(Exception):
    """Raised when registering an email that already exists."""


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_user(
    db: AsyncSession, email: str, password: str, display_name: str | None = None
) -> User:
    email_norm = email.strip().lower()
    if await get_user_by_email(db, email_norm) is not None:
        raise EmailAlreadyExists()

    user = User(
        email=email_norm,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:  # race on the unique index
        await db.rollback()
        raise EmailAlreadyExists() from exc
    await db.refresh(user)
    return user


async def authenticate(
    db: AsyncSession, email: str, password: str
) -> User | None:
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(user.password_hash, password):
        return None
    return user
