"""Usage ledger endpoint (verified provider metadata only, scoped to the user)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.usage import UsageSummaryOut
from app.services import usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=UsageSummaryOut)
async def get_usage(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await usage_service.summary(db, user.id)
