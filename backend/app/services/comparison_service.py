"""Cross-model critique and multi-answer synthesis (Blueprint Ch. 21).

Both read the configured target model, ground it in project memory + the exact
attributed source text, and persist the result as a standard ``assistant``
message with provenance metadata (operation + derived_from_message_ids + the
reviewer/synthesizer provider/model). A synthesis may become the group's
canonical continuation. Provider errors propagate unchanged (owner-enforced
callers map them to 502) and never corrupt stored responses.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import CanonicalMessage, ProviderRequest
from app.adapters.registry import get_adapter
from app.models.conversation import Conversation, Message
from app.models.message_group import MessageGroup
from app.services import (
    conversation_service,
    memory_service,
    project_service,
    target_resolver,
    usage_service,
)

CRITIQUE_SYSTEM = (
    "You are a senior reviewer inside OmniDesk AI. You are given project context "
    "and ONE assistant response produced by another model. Critically evaluate "
    "that response for correctness, security gaps, and alignment with the "
    "project's established decisions and constraints. Be specific and cite "
    "concrete issues; do not rewrite the whole answer. Never imply you have "
    "native access to another provider's account, private history, or tools."
)

SYNTHESIS_SYSTEM = (
    "You are a synthesis engine inside OmniDesk AI. You are given project context "
    "and several assistant responses (from different models) to the same prompt. "
    "Reconcile conflicts, preserve verified technical details, discard mistakes, "
    "and produce ONE unified, coherent answer. Do not attribute sentences to "
    "specific models in the output. Never imply native access to another "
    "provider's account, private history, or tools."
)


async def _project_preamble(db: AsyncSession, project_id: uuid.UUID) -> str:
    instr = await project_service.get_active_instructions(db, project_id)
    decisions = await memory_service.list_active_decisions(db, project_id)
    parts: list[str] = []
    if instr and instr.content:
        parts.append("PROJECT INSTRUCTIONS:\n" + instr.content)
    if decisions:
        lines = [
            f"- {d.title}" + (f" — {d.rationale}" if d.rationale else "")
            for d in decisions
        ]
        parts.append("PROJECT DECISIONS:\n" + "\n".join(lines))
    return "\n\n".join(parts)


def _label(m: Message) -> str:
    return f"[{m.provider or '?'}/{m.model_id or '?'}]"


async def compare(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
    target_provider: str,
    target_model_id: str,
    subject: Message,
    critique_focus: str | None,
) -> tuple[Message, MessageGroup | None]:
    """Have the target model critique ``subject``. Stored as an assistant message
    with operation=critique provenance; NOT auto-selected as a continuation."""
    rp, rm, api_key = await target_resolver.resolve_target(
        db, conversation, user_id, target_provider, target_model_id
    )
    preamble = await _project_preamble(db, conversation.project_id)
    focus = critique_focus or "overall correctness, security gaps, and alignment with project decisions"
    body = (
        (preamble + "\n\n" if preamble else "")
        + f"SUBJECT RESPONSE {_label(subject)}:\n{subject.content}\n\n"
        + f"Critique focus: {focus}\n"
        + "Evaluate correctness, security gaps, and alignment with the project's "
        "decisions and constraints."
    )
    req = ProviderRequest(
        model_id=rm,
        system_prompt=CRITIQUE_SYSTEM,
        messages=[CanonicalMessage(role="user", content=body)],
    )
    resp = await get_adapter(rp).generate(req, api_key)

    message = await conversation_service._append(
        db,
        conversation.id,
        role="assistant",
        content=resp.content,
        provider=resp.provider,
        model_id=resp.model_id,
        status="completed",
        group_id=subject.group_id,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        total_tokens=resp.usage.total_tokens,
        provider_request_id=resp.provider_request_id,
        metadata_json={
            "operation": "critique",
            "subject_message_id": str(subject.id),
            "derived_from_message_ids": [str(subject.id)],
            "reviewer": {"provider": rp, "model_id": rm},
            "subject": {"provider": subject.provider, "model_id": subject.model_id},
        },
    )
    await usage_service.record(db, user_id, conversation, message, resp)
    await db.commit()
    await db.refresh(message)

    group = (
        await db.get(MessageGroup, subject.group_id)
        if subject.group_id is not None
        else None
    )
    return message, group


async def synthesize(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
    target_provider: str,
    target_model_id: str,
    sources: list[Message],
) -> tuple[Message, MessageGroup | None]:
    """Have the target model merge ``sources`` into one answer. Stored with
    operation=synthesis provenance and set as the group's active continuation."""
    rp, rm, api_key = await target_resolver.resolve_target(
        db, conversation, user_id, target_provider, target_model_id
    )
    preamble = await _project_preamble(db, conversation.project_id)
    blocks = [
        f"Response {i} {_label(s)}:\n{s.content}" for i, s in enumerate(sources, 1)
    ]
    body = (
        (preamble + "\n\n" if preamble else "")
        + "\n\n".join(blocks)
        + "\n\nReconcile any conflicts, preserve verified technical details, and "
        "produce one unified answer."
    )
    req = ProviderRequest(
        model_id=rm,
        system_prompt=SYNTHESIS_SYSTEM,
        messages=[CanonicalMessage(role="user", content=body)],
    )
    resp = await get_adapter(rp).generate(req, api_key)

    group_id = next((s.group_id for s in sources if s.group_id is not None), None)
    message = await conversation_service._append(
        db,
        conversation.id,
        role="assistant",
        content=resp.content,
        provider=resp.provider,
        model_id=resp.model_id,
        status="completed",
        group_id=group_id,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        total_tokens=resp.usage.total_tokens,
        provider_request_id=resp.provider_request_id,
        metadata_json={
            "operation": "synthesis",
            "derived_from_message_ids": [str(s.id) for s in sources],
            "synthesizer": {"provider": rp, "model_id": rm},
        },
    )
    await usage_service.record(db, user_id, conversation, message, resp)

    group = await db.get(MessageGroup, group_id) if group_id is not None else None
    if group is not None:
        group.selected_message_id = message.id  # synthesis becomes the continuation
        conversation.active_provider = rp
        conversation.active_model_id = rm
    await db.commit()
    await db.refresh(message)
    if group is not None:
        await db.refresh(group)
    return message, group
