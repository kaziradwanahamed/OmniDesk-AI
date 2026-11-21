"""Shared provider/model/key resolution for a conversation.

Returns (provider, model_id, api_key) and raises ProviderError on misconfiguration
BEFORE any external call. Kept in its own module so the multi-model and
comparison services can resolve targets without importing conversation_service
(avoiding an import cycle). Mirrors conversation_service._resolve_target.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderError
from app.models.conversation import Conversation
from app.services import provider_key_service

DEFAULT_PROVIDER = "stub"
DEFAULT_MODEL = "stub-echo"


async def resolve_target(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
    provider: str | None,
    model_id: str | None,
) -> tuple[str, str, str | None]:
    provider = provider or conversation.active_provider or DEFAULT_PROVIDER
    if provider == "stub":
        return "stub", (model_id or DEFAULT_MODEL), None

    config = await provider_key_service.get_config(db, user_id, provider)
    api_key = await provider_key_service.resolve_key(db, user_id, provider, config)
    if not api_key:
        raise ProviderError(
            "AUTH_INVALID_KEY",
            f"No API key configured for {provider}. Add one in Provider Settings.",
        )
    enabled = list(config.enabled_models) if config else []
    model_id = model_id or conversation.active_model_id or (enabled[0] if enabled else None)
    if not model_id:
        raise ProviderError(
            "MODEL_UNAVAILABLE",
            "No model selected. Enable a model in Provider Settings.",
        )
    if enabled and model_id not in enabled:
        raise ProviderError(
            "MODEL_UNAVAILABLE", f"Model '{model_id}' is not enabled for {provider}."
        )
    return provider, model_id, api_key
