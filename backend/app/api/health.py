"""Liveness and readiness probes.

``/health`` is a pure liveness check (the process is up). ``/ready`` additionally
verifies PostgreSQL connectivity with ``SELECT 1`` and returns HTTP 503 if the
database is unreachable. Both are mounted at the root (outside ``/api/v1``) so
container orchestrators and the reverse proxy can probe them directly.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger("omnidesk.health")

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is running and serving requests."""
    return {"status": "ok"}


@router.get("/ready", response_model=None)
async def ready() -> JSONResponse | dict[str, str]:
    """Readiness: the process can reach PostgreSQL."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - never surface DB internals to clients
        logger.exception("Readiness check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )
    return {"status": "ready", "database": "connected"}
