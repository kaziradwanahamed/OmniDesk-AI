"""Project export: a clean, ownership-checked Markdown or JSON archive of a
project's persistent memory and conversations (Blueprint Ch. 10, Phase 9).

Reads canonical rows only; it never calls a provider or fabricates data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import Attachment
from app.models.context_summary import ConversationSummary
from app.models.conversation import Conversation, Message
from app.models.project import (
    Project,
    ProjectDecision,
    ProjectInstruction,
    ProjectTask,
)


async def _gather(db: AsyncSession, project: Project) -> dict:
    instructions = (
        await db.execute(
            select(ProjectInstruction)
            .where(
                ProjectInstruction.project_id == project.id,
                ProjectInstruction.is_active.is_(True),
            )
            .order_by(ProjectInstruction.version.desc())
        )
    ).scalars().first()

    decisions = list(
        (
            await db.execute(
                select(ProjectDecision)
                .where(ProjectDecision.project_id == project.id)
                .order_by(ProjectDecision.created_at.asc())
            )
        ).scalars().all()
    )
    tasks = list(
        (
            await db.execute(
                select(ProjectTask)
                .where(ProjectTask.project_id == project.id)
                .order_by(ProjectTask.updated_at.asc())
            )
        ).scalars().all()
    )
    files = list(
        (
            await db.execute(
                select(Attachment)
                .where(Attachment.project_id == project.id)
                .order_by(Attachment.created_at.asc())
            )
        ).scalars().all()
    )
    conversations = list(
        (
            await db.execute(
                select(Conversation)
                .where(Conversation.project_id == project.id)
                .order_by(Conversation.created_at.asc())
            )
        ).scalars().all()
    )

    convs: list[dict] = []
    for conv in conversations:
        messages = list(
            (
                await db.execute(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.sequence_no.asc())
                )
            ).scalars().all()
        )
        summary = (
            await db.execute(
                select(ConversationSummary).where(
                    ConversationSummary.conversation_id == conv.id,
                    ConversationSummary.is_active.is_(True),
                )
            )
        ).scalars().first()
        convs.append({"conversation": conv, "messages": messages, "summary": summary})

    return {
        "instructions": instructions,
        "decisions": decisions,
        "tasks": tasks,
        "files": files,
        "conversations": convs,
    }


def _project_dict(project: Project, data: dict) -> dict:
    instr = data["instructions"]
    return {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "goals": project.goals,
            "tech_stack": project.tech_stack,
            "status": project.status,
            "progress_notes": project.progress_notes,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        },
        "instructions": (
            {"content": instr.content, "response_style": instr.response_style,
             "version": instr.version}
            if instr
            else None
        ),
        "decisions": [
            {"title": d.title, "rationale": d.rationale, "status": d.status}
            for d in data["decisions"]
        ],
        "tasks": [
            {
                "title": t.title,
                "details": t.details,
                "status": t.status,
                "is_active_task": t.is_active_task,
            }
            for t in data["tasks"]
        ],
        "files": [
            {
                "filename": f.filename,
                "extension": f.extension,
                "size_bytes": f.size_bytes,
                "extraction_status": f.extraction_status,
                "chunk_count": f.chunk_count,
                "pinned": f.pinned,
                "sha256": f.sha256,
            }
            for f in data["files"]
        ],
        "conversations": [
            {
                "title": c["conversation"].title,
                "active_provider": c["conversation"].active_provider,
                "active_model_id": c["conversation"].active_model_id,
                "summary": (
                    {"version": c["summary"].version, "content": c["summary"].content}
                    if c["summary"]
                    else None
                ),
                "messages": [
                    {
                        "sequence_no": m.sequence_no,
                        "role": m.role,
                        "provider": m.provider,
                        "model_id": m.model_id,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in c["messages"]
                ],
            }
            for c in data["conversations"]
        ],
    }


def _render_markdown(payload: dict) -> str:
    p = payload["project"]
    out: list[str] = [f"# Project Export: {p['name']}", ""]
    out.append(f"_Exported {datetime.now(timezone.utc).isoformat()}_")
    out.append("")
    out.append("## Overview")
    for label, key in (
        ("Description", "description"),
        ("Goals", "goals"),
        ("Tech stack", "tech_stack"),
        ("Status", "status"),
        ("Progress", "progress_notes"),
    ):
        if p.get(key):
            out.append(f"- **{label}:** {p[key]}")
    out.append("")

    if payload["instructions"]:
        out.append("## Project Instructions")
        out.append(payload["instructions"]["content"])
        if payload["instructions"].get("response_style"):
            out.append("")
            out.append(f"_Response style: {payload['instructions']['response_style']}_")
        out.append("")

    if payload["decisions"]:
        out.append("## Key Decisions")
        for d in payload["decisions"]:
            line = f"- **{d['title']}**"
            if d.get("rationale"):
                line += f" — {d['rationale']}"
            line += f" _({d['status']})_"
            out.append(line)
        out.append("")

    if payload["tasks"]:
        out.append("## Tasks")
        for t in payload["tasks"]:
            marker = "▶ " if t["is_active_task"] else ""
            line = f"- {marker}**{t['title']}** _({t['status']})_"
            if t.get("details"):
                line += f" — {t['details']}"
            out.append(line)
        out.append("")

    if payload["files"]:
        out.append("## Files")
        for f in payload["files"]:
            pin = " · pinned" if f["pinned"] else ""
            out.append(
                f"- `{f['filename']}` ({f['extension']}, {f['size_bytes']} bytes, "
                f"{f['extraction_status']}, {f['chunk_count']} chunks{pin})"
            )
        out.append("")

    out.append("## Conversations")
    out.append("")
    for c in payload["conversations"]:
        header = f"### {c['title']}"
        if c["active_provider"]:
            header += f" ({c['active_provider']}/{c['active_model_id']})"
        out.append(header)
        if c["summary"]:
            out.append("")
            out.append(f"_Rolling summary (v{c['summary']['version']}):_ {c['summary']['content']}")
        out.append("")
        for m in c["messages"]:
            if m["role"] == "system_event":
                out.append(f"> _{m['content']}_")
                out.append("")
                continue
            who = m["role"]
            if m["role"] == "assistant" and m["provider"]:
                who = f"assistant [{m['provider']}/{m['model_id']}]"
            out.append(f"**{who}:**")
            out.append("")
            out.append(m["content"])
            out.append("")
    return "\n".join(out).rstrip() + "\n"


async def export_project(
    db: AsyncSession, project: Project, fmt: str
) -> tuple[str, str, str]:
    """Return ``(content, media_type, filename)`` for a project export.

    ``fmt`` must be ``md`` or ``json`` (validated by the caller)."""
    data = await _gather(db, project)
    payload = _project_dict(project, data)
    slug = "".join(ch if ch.isalnum() else "-" for ch in project.name).strip("-").lower() or "project"
    if fmt == "json":
        return (
            json.dumps(payload, indent=2, ensure_ascii=False),
            "application/json",
            f"{slug}-export.json",
        )
    return _render_markdown(payload), "text/markdown", f"{slug}-export.md"
