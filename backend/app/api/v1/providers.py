"""Provider configuration endpoints: keys (masked), connection test, enabled models."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import SUPPORTED_PROVIDERS
from app.api.deps import get_current_user, require_csrf
from app.db.session import get_db
from app.models.provider_config import ProviderConfig
from app.models.user import User
from app.schemas.provider_config import (
    EnabledModelsIn,
    ProviderConfigOut,
    ProviderKeyIn,
    TestConnectionOut,
)
from app.services import provider_key_service

router = APIRouter(prefix="/providers", tags=["providers"])


def _config_out(cfg: ProviderConfig | None, provider: str) -> ProviderConfigOut:
    if cfg is None:
        return ProviderConfigOut(
            provider=provider,
            configured=False,
            key_hint=None,
            enabled_models=[],
            is_enabled=True,
        )
    return ProviderConfigOut(
        provider=cfg.provider,
        configured=cfg.encrypted_api_key is not None,
        key_hint=cfg.key_hint,
        enabled_models=list(cfg.enabled_models),
        is_enabled=cfg.is_enabled,
    )


def _require_supported(provider: str) -> None:
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' is not supported yet.",
        )


@router.get("", response_model=list[ProviderConfigOut])
async def list_providers(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    configs = {c.provider: c for c in await provider_key_service.list_configs(db, user.id)}
    return [_config_out(configs.get(p), p) for p in SUPPORTED_PROVIDERS]


@router.put(
    "/{provider}/key",
    response_model=ProviderConfigOut,
    dependencies=[Depends(require_csrf)],
)
async def set_key(
    provider: str,
    data: ProviderKeyIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_supported(provider)
    cfg = await provider_key_service.set_key(db, user.id, provider, data.api_key)
    return _config_out(cfg, provider)


@router.delete(
    "/{provider}/key",
    response_model=ProviderConfigOut,
    dependencies=[Depends(require_csrf)],
)
async def delete_key(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_supported(provider)
    cfg = await provider_key_service.delete_key(db, user.id, provider)
    return _config_out(cfg, provider)


@router.post(
    "/{provider}/test",
    response_model=TestConnectionOut,
    dependencies=[Depends(require_csrf)],
)
async def test_connection(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_supported(provider)
    ok, models, category, message = await provider_key_service.test_connection(
        db, user.id, provider
    )
    return TestConnectionOut(ok=ok, models=models, category=category, message=message)


@router.put(
    "/{provider}/models",
    response_model=ProviderConfigOut,
    dependencies=[Depends(require_csrf)],
)
async def set_models(
    provider: str,
    data: EnabledModelsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_supported(provider)
    cfg = await provider_key_service.set_enabled_models(
        db, user.id, provider, data.enabled_models
    )
    return _config_out(cfg, provider)
