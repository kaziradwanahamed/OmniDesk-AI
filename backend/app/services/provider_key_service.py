"""Provider API-key management: encrypted storage, resolution, and connectivity test."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderError
from app.adapters.registry import get_adapter
from app.core import crypto
from app.core.config import get_settings
from app.models.provider_config import ProviderConfig

# Server-env fallback keys (used only when a user has no per-user key stored).
_ENV_FALLBACK: dict[str, Callable[[], str | None]] = {
    "openai": lambda: get_settings().openai_api_key,
}


async def get_config(
    db: AsyncSession, user_id: uuid.UUID, provider: str
) -> ProviderConfig | None:
    stmt = select(ProviderConfig).where(
        ProviderConfig.user_id == user_id, ProviderConfig.provider == provider
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_configs(
    db: AsyncSession, user_id: uuid.UUID
) -> list[ProviderConfig]:
    stmt = select(ProviderConfig).where(ProviderConfig.user_id == user_id)
    return list((await db.execute(stmt)).scalars().all())


async def _get_or_create(
    db: AsyncSession, user_id: uuid.UUID, provider: str
) -> ProviderConfig:
    cfg = await get_config(db, user_id, provider)
    if cfg is None:
        cfg = ProviderConfig(user_id=user_id, provider=provider)
        db.add(cfg)
    return cfg


async def set_key(
    db: AsyncSession, user_id: uuid.UUID, provider: str, api_key: str
) -> ProviderConfig:
    cfg = await _get_or_create(db, user_id, provider)
    cfg.encrypted_api_key = crypto.encrypt(api_key)
    cfg.key_hint = crypto.key_hint(api_key)
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def delete_key(
    db: AsyncSession, user_id: uuid.UUID, provider: str
) -> ProviderConfig | None:
    cfg = await get_config(db, user_id, provider)
    if cfg is None:
        return None
    cfg.encrypted_api_key = None
    cfg.key_hint = None
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def set_enabled_models(
    db: AsyncSession, user_id: uuid.UUID, provider: str, models: list[str]
) -> ProviderConfig:
    cfg = await _get_or_create(db, user_id, provider)
    # Dedupe while preserving order.
    cfg.enabled_models = list(dict.fromkeys(m for m in models if m))
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def resolve_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    config: ProviderConfig | None = None,
) -> str | None:
    """Decrypted key: the user's stored key, else the server-env fallback."""
    cfg = config if config is not None else await get_config(db, user_id, provider)
    if cfg is not None and cfg.encrypted_api_key:
        try:
            return crypto.decrypt(cfg.encrypted_api_key)
        except crypto.DecryptionError:
            return None
    fallback = _ENV_FALLBACK.get(provider)
    if fallback:
        value = fallback()
        if value:
            return value
    return None


async def test_connection(
    db: AsyncSession, user_id: uuid.UUID, provider: str
) -> tuple[bool, list[str], str | None, str | None]:
    """Return (ok, model_ids, error_category, error_message)."""
    api_key = await resolve_key(db, user_id, provider)
    if not api_key:
        return (False, [], "AUTH_INVALID_KEY", "No API key configured.")
    adapter = get_adapter(provider)
    try:
        models = await adapter.list_models(api_key)
        return (True, models, None, None)
    except ProviderError as err:
        return (False, [], err.category, err.user_message)
