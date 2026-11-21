"""Versioned API router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    context,
    conversations,
    memory,
    projects,
    providers,
    summaries,
    usage,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(memory.router)
api_router.include_router(conversations.router)
api_router.include_router(context.router)
api_router.include_router(summaries.router)
api_router.include_router(providers.router)
api_router.include_router(usage.router)
