"""FastAPI application factory for OmniDesk AI.

Phase 1 wires configuration, structured + redacting logging, CORS for the local
frontend, a generic exception handler that never leaks internals, a lifespan that
disposes the async DB engine on shutdown, and the health/readiness router. Domain
routers (auth, projects, conversations, ...) arrive in later phases.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("omnidesk.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OmniDesk AI backend starting (env=%s)", settings.app_env)
    yield
    # Import lazily so the engine is created only when actually needed.
    from app.db.session import engine

    await engine.dispose()
    logger.info("OmniDesk AI backend stopped; DB engine disposed")


def create_app() -> FastAPI:
    app = FastAPI(title="OmniDesk AI", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log full detail (redacted by the logging filter); return a generic body.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
