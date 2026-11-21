"""Security primitives: Argon2id password hashing, JWT sessions, CSRF, cookies."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Response

from app.core.config import get_settings

_settings = get_settings()
_ph = PasswordHasher()

ALGORITHM = "HS256"
ACCESS_COOKIE = "access_token"
CSRF_COOKIE = "csrf_token"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, Exception):  # noqa: BLE001
        return False


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=_settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a session token. Raises jwt.PyJWTError if invalid."""
    return jwt.decode(token, _settings.jwt_secret_key, algorithms=[ALGORITHM])


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _max_age() -> int:
    return _settings.access_token_expire_minutes * 60


def set_auth_cookies(response: Response, access_token: str, csrf_token: str) -> None:
    """Set the HttpOnly session cookie and the (JS-readable) double-submit CSRF cookie."""
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=_max_age(),
        httponly=True,
        secure=_settings.cookie_secure,
        samesite=_settings.cookie_samesite,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=_max_age(),
        httponly=False,  # readable by the frontend to echo as X-CSRF-Token
        secure=_settings.cookie_secure,
        samesite=_settings.cookie_samesite,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
