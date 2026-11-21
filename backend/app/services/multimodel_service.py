"""Multi-model parallel fan-out (Blueprint Ch. 20).

Sends one prompt to several configured models concurrently and saves every
successful response independently (own provider/model/usage), linked by a
``message_group``. Partial failure is isolated: a provider error on one model
never discards the others and never loses the prompt. The group's
``selected_message_id`` (defaulting to the first success) is what future context
includes — the N responses never triple future token usage.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderError, ProviderResponse
from app.adapters.registry import get_adapter
from app.models.conversation import Conversation, Message
from app.models.message_group import MessageGroup
from app.services import (
    context_builder,
    conversation_service,
    target_resolver,
    usage_service,
)


async def _call(provider: str, request, api_key: str | None) -> tuple[ProviderResponse, int]:
    adapter = get_adapter(provider)
    started = time.perf_counter()
    resp = await adapter.generate(request, api_key)
    return resp, int((time.perf_counter() - started) * 1000)


async def multi_send(
    db: AsyncSession,
    conversation: Conversation,
    content: str,
    user_id: uuid.UUID,
    targets: list[tuple[str, str | None]],
    retry_message_id: uuid.UUID | None = None,
) -> tuple[MessageGroup, Message, list[dict]]:
    """Fan out ``content`` to each (provider, model_id) target concurrently.

    Returns (group, user_message, responses) where each response is a dict with
    ``provider``/``model_id`` and exactly one of ``message`` (persisted) or
    ``error`` (a ProviderError). Order matches ``targets`` (deduplicated)."""
    # Deduplicate targets, preserving order.
    deduped: list[tuple[str, str | None]] = []
    for t in targets:
        if t not in deduped:
            deduped.append(t)
    if not deduped:
        raise ProviderError("MODEL_UNAVAILABLE", "No models selected.")

    # 1. Persist the user prompt once (write-ahead; reused on retry).
    user_msg = await conversation_service._resolve_user_message(
        db, conversation.id, content, retry_message_id
    )

    group = MessageGroup(
        conversation_id=conversation.id,
        user_message_id=user_msg.id,
        kind="parallel",
        metadata_json={
            "targets": [{"provider": p, "model_id": m} for p, m in deduped]
        },
    )
    db.add(group)
    await db.flush()

    # 2. Resolve + build each per-provider context package sequentially (DB work),
    #    recording resolution failures per target without an external call.
    prepared: list[dict] = []
    for provider, model_id in deduped:
        try:
            rp, rm, key = await target_resolver.resolve_target(
                db, conversation, user_id, provider, model_id
            )
            built = await context_builder.build(
                db,
                conversation=conversation,
                target_provider=rp,
                target_model_id=rm,
                user_message_content=content,
                exclude_message_id=user_msg.id,
                persist=True,
            )
            prepared.append(
                {
                    "provider": rp,
                    "model_id": rm,
                    "api_key": key,
                    "request": built.provider_request,
                    "snapshot_id": built.snapshot_id,
                    "error": None,
                }
            )
        except ProviderError as err:
            prepared.append(
                {"provider": provider, "model_id": model_id, "error": err}
            )
    await db.commit()  # persist user message + group + snapshots

    # 3. Concurrent adapter calls — network only, NO shared-session DB access.
    callable_items = [p for p in prepared if p["error"] is None]
    results = await asyncio.gather(
        *[_call(p["provider"], p["request"], p["api_key"]) for p in callable_items],
        return_exceptions=True,
    )
    result_by_id = {id(p): r for p, r in zip(callable_items, results)}

    # 4. Persist results sequentially, preserving every success.
    responses: list[dict] = []
    first_success: Message | None = None
    for p in prepared:
        if p["error"] is not None:
            responses.append(
                {"provider": p["provider"], "model_id": p["model_id"], "message": None, "error": p["error"]}
            )
            continue
        r = result_by_id[id(p)]
        if isinstance(r, ProviderError):
            responses.append(
                {"provider": p["provider"], "model_id": p["model_id"], "message": None, "error": r}
            )
            continue
        if isinstance(r, BaseException):
            responses.append(
                {
                    "provider": p["provider"],
                    "model_id": p["model_id"],
                    "message": None,
                    "error": ProviderError("MODEL_UNAVAILABLE", "Provider call failed."),
                }
            )
            continue
        resp, latency = r
        assistant = await conversation_service._append(
            db,
            conversation.id,
            role="assistant",
            content=resp.content,
            provider=resp.provider,
            model_id=resp.model_id,
            status="completed",
            group_id=group.id,
            context_snapshot_id=p["snapshot_id"],
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.total_tokens,
            latency_ms=latency,
            provider_request_id=resp.provider_request_id,
        )
        await usage_service.record(db, user_id, conversation, assistant, resp)
        responses.append(
            {"provider": resp.provider, "model_id": resp.model_id, "message": assistant, "error": None}
        )
        if first_success is None:
            first_success = assistant

    # 5. Default the group's continuation to the first success; set active model.
    if first_success is not None:
        group.selected_message_id = first_success.id
        conversation.active_provider = first_success.provider
        conversation.active_model_id = first_success.model_id
    await db.commit()

    await db.refresh(group)
    await db.refresh(user_msg)
    for resp_item in responses:
        if resp_item["message"] is not None:
            await db.refresh(resp_item["message"])
    return group, user_msg, responses


async def select_group_message(
    db: AsyncSession, group: MessageGroup, message: Message
) -> MessageGroup:
    """Set the group's active continuation and align the conversation's active
    model to it (so the inspector + next turn reflect the chosen response)."""
    group.selected_message_id = message.id
    conv = await db.get(Conversation, group.conversation_id)
    if conv is not None and message.provider:
        conv.active_provider = message.provider
        conv.active_model_id = message.model_id
    await db.commit()
    await db.refresh(group)
    return group
