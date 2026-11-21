"""Project file (attachment) endpoints — owner-enforced upload, list, inspect,
pin/rename, download, and delete (Blueprint Ch. 22 & 27)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    require_attachment_owner,
    require_csrf,
    require_project_owner,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.attachment import Attachment, AttachmentChunk
from app.models.project import Project
from app.schemas.attachment import (
    AttachmentChunkOut,
    AttachmentOut,
    AttachmentUpdate,
    AttachmentUploadOut,
)
from app.services import file_service

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


@router.get("", response_model=list[AttachmentOut])
async def list_files(
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    return await file_service.list_attachments(db, project.id)


@router.post(
    "",
    response_model=AttachmentUploadOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def upload_file(
    file: UploadFile = File(...),
    project: Project = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    # Read at most one byte past the cap so an oversize upload is bounded in memory.
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        attachment, deduplicated = await file_service.store_file(
            db,
            project.id,
            file.filename or "upload",
            file.content_type,
            data,
        )
    except file_service.FileValidationError as err:
        raise HTTPException(status_code=err.status_code, detail=err.message)
    await db.commit()
    await db.refresh(attachment)
    out = AttachmentUploadOut.model_validate(attachment)
    out.deduplicated = deduplicated
    return out


@router.get("/{attachment_id}", response_model=AttachmentOut)
async def get_file(attachment: Attachment = Depends(require_attachment_owner)):
    return attachment


@router.get("/{attachment_id}/chunks", response_model=list[AttachmentChunkOut])
async def list_chunks(
    attachment: Attachment = Depends(require_attachment_owner),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AttachmentChunk)
        .where(AttachmentChunk.attachment_id == attachment.id)
        .order_by(AttachmentChunk.chunk_index.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{attachment_id}/download")
async def download_file(attachment: Attachment = Depends(require_attachment_owner)):
    """Serve the raw file as an attachment (never inline) so a malicious upload
    cannot be rendered in the browser."""
    try:
        path = file_service.resolve_storage_path(attachment.storage_key)
        data = path.read_bytes()
    except (file_service.FileValidationError, FileNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File content not found"
        )
    safe_name = file_service.sanitize_filename(attachment.filename)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/{attachment_id}",
    response_model=AttachmentOut,
    dependencies=[Depends(require_csrf)],
)
async def update_file(
    data: AttachmentUpdate,
    attachment: Attachment = Depends(require_attachment_owner),
    db: AsyncSession = Depends(get_db),
):
    updated = await file_service.update_attachment(
        db, attachment, pinned=data.pinned, filename=data.filename
    )
    await db.commit()
    await db.refresh(updated)
    return updated


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_file(
    attachment: Attachment = Depends(require_attachment_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    await file_service.delete_attachment(db, attachment)
    await db.commit()
    return None
