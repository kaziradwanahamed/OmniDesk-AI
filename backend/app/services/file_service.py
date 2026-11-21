"""Project file service: secure upload, text extraction, deterministic chunking,
and lexical (PostgreSQL full-text) retrieval for ContextBuilder Layer 5.

Security posture (Blueprint Ch. 22 & 27):
- Strict extension + MIME allowlist and a hard size cap; PDFs and text are
  content-sniffed (magic bytes / UTF-8) so a disguised binary is rejected.
- Files are written under server-generated UUID keys inside a backend-only upload
  root; user filenames are sanitized to a basename and never trusted on disk, and
  every resolved path is contained within the root (``Path.resolve`` check).
- Per-project SHA-256 deduplication; uploaded files are never executed.

Retrieval stays on native PostgreSQL ``ts_rank_cd`` plus explicit pins — no vector
DB / embedding dependency (added only if lexical search proves insufficient).

This module imports only models + the shared token estimator, never
ContextBuilder or conversation_service, so it can be used from Layer 5 assembly
without an import cycle.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.attachment import Attachment, AttachmentChunk
from app.services.token_estimate import chars_for_tokens, estimate_tokens

# ------------------------------- Allowlists ----------------------------------

# Extension -> acceptable declared MIME types. Code editors and browsers mislabel
# code files wildly, so a generic/empty type is also accepted (see _GENERIC_MIME);
# the real gate is the extension allowlist plus content sniffing below.
_EXT_MIME: dict[str, set[str]] = {
    ".md": {"text/markdown", "text/x-markdown", "text/plain"},
    ".txt": {"text/plain"},
    ".py": {"text/x-python", "application/x-python", "text/x-python-script", "text/plain"},
    ".ts": {"application/typescript", "text/typescript", "video/mp2t", "text/plain"},
    ".tsx": {"application/typescript", "text/typescript", "text/plain"},
    ".json": {"application/json", "text/json", "text/plain"},
    ".yaml": {"application/x-yaml", "application/yaml", "text/yaml", "text/plain"},
    ".yml": {"application/x-yaml", "application/yaml", "text/yaml", "text/plain"},
    ".sql": {"application/sql", "text/x-sql", "text/sql", "text/plain"},
    ".csv": {"text/csv", "application/csv", "text/plain"},
    ".pdf": {"application/pdf"},
}
# Accepted for any allowed extension (browsers send these for code files).
_GENERIC_MIME: set[str] = {"", "application/octet-stream"}

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(_EXT_MIME)


class FileValidationError(Exception):
    """Raised for a rejected upload. ``status_code`` is the HTTP code to return
    (400 for a bad type/content, 413 for oversize)."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


# ------------------------------- Disk storage --------------------------------


def _upload_root() -> Path:
    """Backend-only upload directory (created on demand). Overridable in tests."""
    return Path(get_settings().upload_dir)


def resolve_storage_path(storage_key: str) -> Path:
    """Resolve ``storage_key`` under the upload root, rejecting anything that
    escapes it (defense-in-depth; keys are server-generated UUIDs)."""
    root = _upload_root().resolve()
    candidate = (root / storage_key).resolve()
    if not candidate.is_relative_to(root):
        raise FileValidationError(400, "Invalid storage path.")
    return candidate


def sanitize_filename(name: str) -> str:
    """Reduce a client filename to a safe display basename (no directories, no
    NUL/control chars, length-capped). Never used as a disk path."""
    base = os.path.basename(name.replace("\\", "/")).strip()
    base = base.lstrip(".") if base in ("", ".", "..") else base
    base = "".join(ch for ch in base if ch == "\t" or ord(ch) >= 32).strip()
    base = base.replace("\t", " ")
    if not base or base in (".", ".."):
        base = "upload"
    return base[:255]


def extension_of(name: str) -> str:
    return os.path.splitext(name)[1].lower()


# ------------------------------- Validation ----------------------------------


def validate_upload(filename: str, content_type: str | None, data: bytes) -> tuple[str, str]:
    """Validate an upload and return ``(extension, normalized_mime)``.

    Raises :class:`FileValidationError` (400 bad type/content, 413 oversize)."""
    settings = get_settings()
    ext = extension_of(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            400,
            f"Unsupported file type '{ext or filename}'. Allowed: "
            + ", ".join(sorted(ALLOWED_EXTENSIONS)),
        )

    if len(data) > settings.max_upload_bytes:
        mb = settings.max_upload_bytes / (1024 * 1024)
        raise FileValidationError(
            413, f"File too large. Maximum size is {mb:.0f} MB."
        )

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime not in _EXT_MIME[ext] and mime not in _GENERIC_MIME:
        raise FileValidationError(
            400,
            f"Declared content type '{content_type}' is not allowed for a "
            f"'{ext}' file.",
        )

    # Content sniffing — reject disguised binaries.
    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise FileValidationError(400, "File is not a valid PDF (bad header).")
    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise FileValidationError(
                400, "File is not valid UTF-8 text."
            ) from None
    return ext, (mime or "application/octet-stream")


# ------------------------------ Text extraction ------------------------------


@dataclass
class ExtractionResult:
    status: str  # extracted | empty | encrypted | failed
    text: str
    error: str | None = None
    # (char_start, char_end, page_number) spans for PDFs; None for text/code.
    page_spans: list[tuple[int, int, int]] | None = None


def extract_text(ext: str, data: bytes) -> ExtractionResult:
    """Extract text safely. Corrupted/encrypted/empty files yield a status, never
    an exception that crashes the request."""
    if ext == ".pdf":
        return _extract_pdf(data)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:  # already validated, but stay defensive
        return ExtractionResult("failed", "", f"decode error: {exc}", None)
    return ExtractionResult("extracted" if text.strip() else "empty", text, None, None)


def _extract_pdf(data: bytes) -> ExtractionResult:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            try:
                if not reader.decrypt(""):  # try empty password
                    return ExtractionResult(
                        "encrypted", "", "PDF is password-protected.", None
                    )
            except Exception:  # noqa: BLE001 — treat any decrypt failure as encrypted
                return ExtractionResult(
                    "encrypted", "", "PDF is password-protected.", None
                )

        parts: list[str] = []
        spans: list[tuple[int, int, int]] = []
        for i, page in enumerate(reader.pages):
            try:
                ptext = page.extract_text() or ""
            except Exception:  # noqa: BLE001 — a bad page must not sink the file
                ptext = ""
            if not ptext:
                continue
            start = sum(len(p) for p in parts) + len(parts)  # prior chars + joiners
            parts.append(ptext)
            spans.append((start, start + len(ptext), i + 1))
        text = "\n".join(parts)
        if not text.strip():
            return ExtractionResult("empty", "", None, None)
        return ExtractionResult("extracted", text, None, spans or None)
    except Exception as exc:  # noqa: BLE001 — corrupted PDF
        return ExtractionResult("failed", "", f"PDF parse error: {exc}"[:500], None)


# -------------------------------- Chunking -----------------------------------


@dataclass
class ChunkData:
    chunk_index: int
    content: str
    token_est: int
    char_start: int
    char_end: int
    start_line: int | None = None
    end_line: int | None = None
    page_start: int | None = None
    page_end: int | None = None


def _page_at(pos: int, spans: list[tuple[int, int, int]]) -> int | None:
    page = None
    for start, end, number in spans:
        if start <= pos < end:
            return number
        if start <= pos:
            page = number  # fall back to the last page that began at/before pos
    return page


def chunk_text(
    text: str, page_spans: list[tuple[int, int, int]] | None = None
) -> list[ChunkData]:
    """Deterministic overlapping character-window chunking (~target tokens with
    an overlap). Window ends snap back to the nearest whitespace in the tail so
    chunks don't split mid-word, while the step stays fixed for a stable overlap."""
    settings = get_settings()
    target = max(1, chars_for_tokens(settings.chunk_target_tokens))
    overlap = max(0, chars_for_tokens(settings.chunk_overlap_tokens))
    overlap = min(overlap, target - 1)

    n = len(text)
    chunks: list[ChunkData] = []
    if not text.strip():
        return chunks

    start = 0
    idx = 0
    while start < n:
        end = min(start + target, n)
        if end < n:  # snap to a whitespace boundary in the last part of the window
            window = text[start:end]
            snap = max(window.rfind("\n"), window.rfind(" "))
            if snap > int(target * 0.6):
                end = start + snap + 1
        content = text[start:end]
        if content.strip():
            cd = ChunkData(
                chunk_index=idx,
                content=content,
                token_est=estimate_tokens(content),
                char_start=start,
                char_end=end,
            )
            if page_spans:
                cd.page_start = _page_at(start, page_spans)
                cd.page_end = _page_at(max(start, end - 1), page_spans)
            else:
                cd.start_line = text.count("\n", 0, start) + 1
                cd.end_line = text.count("\n", 0, max(start, end - 1)) + 1
            chunks.append(cd)
            idx += 1
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


# ------------------------------- Persistence ---------------------------------


async def list_attachments(db: AsyncSession, project_id: uuid.UUID) -> list[Attachment]:
    stmt = (
        select(Attachment)
        .where(Attachment.project_id == project_id)
        .order_by(Attachment.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _find_by_hash(
    db: AsyncSession, project_id: uuid.UUID, sha256: str
) -> Attachment | None:
    stmt = select(Attachment).where(
        Attachment.project_id == project_id, Attachment.sha256 == sha256
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def store_file(
    db: AsyncSession,
    project_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> tuple[Attachment, bool]:
    """Validate, deduplicate, persist to disk, extract + chunk. Returns
    ``(attachment, deduplicated)``. Raises :class:`FileValidationError` on a
    rejected upload (before anything is written). Caller commits."""
    ext, mime = validate_upload(filename, content_type, data)
    display_name = sanitize_filename(filename)
    sha = hashlib.sha256(data).hexdigest()

    existing = await _find_by_hash(db, project_id, sha)
    if existing is not None:
        return existing, True

    storage_key = f"{uuid.uuid4().hex}{ext}"
    disk_path = resolve_storage_path(storage_key)
    disk_path.parent.mkdir(parents=True, exist_ok=True)
    disk_path.write_bytes(data)

    attachment = Attachment(
        project_id=project_id,
        filename=display_name,
        extension=ext,
        mime_type=mime,
        size_bytes=len(data),
        sha256=sha,
        storage_key=storage_key,
        extraction_status="pending",
    )
    db.add(attachment)
    await db.flush()  # assign attachment.id

    result = extract_text(ext, data)
    attachment.extraction_status = result.status
    attachment.extraction_error = result.error
    if result.status == "extracted":
        chunks = chunk_text(result.text, result.page_spans)
        for cd in chunks:
            db.add(
                AttachmentChunk(
                    attachment_id=attachment.id,
                    chunk_index=cd.chunk_index,
                    content=cd.content,
                    token_est=cd.token_est,
                    char_start=cd.char_start,
                    char_end=cd.char_end,
                    start_line=cd.start_line,
                    end_line=cd.end_line,
                    page_start=cd.page_start,
                    page_end=cd.page_end,
                )
            )
        attachment.chunk_count = len(chunks)
    await db.flush()
    return attachment, False


async def update_attachment(
    db: AsyncSession,
    attachment: Attachment,
    *,
    pinned: bool | None = None,
    filename: str | None = None,
) -> Attachment:
    """Pin/unpin or rename (display only — the disk file is untouched). Caller
    commits."""
    if pinned is not None:
        attachment.pinned = pinned
    if filename is not None:
        attachment.filename = sanitize_filename(filename)
    await db.flush()
    return attachment


async def delete_attachment(db: AsyncSession, attachment: Attachment) -> None:
    """Delete DB rows (chunks cascade) and the on-disk file. Caller commits."""
    try:
        resolve_storage_path(attachment.storage_key).unlink(missing_ok=True)
    except FileValidationError:
        pass  # key failed containment — never touch anything outside the root
    await db.delete(attachment)


# -------------------------------- Retrieval ----------------------------------


@dataclass
class RetrievedExcerpt:
    attachment_id: uuid.UUID
    filename: str
    chunk_index: int
    token_est: int
    pinned: bool
    matched: bool
    rank: float | None = None
    content: str = ""  # internal; not surfaced in the inspector payload


@dataclass
class RetrievalResult:
    text: str
    included: list[RetrievedExcerpt] = field(default_factory=list)
    dropped: list[RetrievedExcerpt] = field(default_factory=list)

    @property
    def token_total(self) -> int:
        return estimate_tokens(self.text) if self.text else 0


def _format_excerpt(filename: str, chunk_index: int, content: str) -> str:
    # 1-based chunk label for humans (Blueprint: "[File: architecture.md | Chunk 3]").
    return f"[File: {filename} | Chunk {chunk_index + 1}]\n{content}"


async def retrieve_excerpts(
    db: AsyncSession,
    project_id: uuid.UUID,
    query: str,
    include_file_ids: list[uuid.UUID],
    token_budget: int,
) -> RetrievalResult:
    """Assemble Layer 5: pinned/explicitly-included file chunks first (priority),
    then top ``ts_rank_cd`` matches for ``query``, greedily fit to ``token_budget``.

    Strictly scoped to ``project_id`` — ``include_file_ids`` pointing at another
    project's files are filtered out by the project predicate, so no cross-project
    excerpt can ever leak."""
    if token_budget <= 0:
        return RetrievalResult("")

    seen: set[uuid.UUID] = set()
    ordered: list[RetrievedExcerpt] = []

    # 1. Pinned (attachment.pinned) + explicitly included (this turn), project-scoped.
    pinned_stmt = (
        select(AttachmentChunk, Attachment.filename)
        .join(Attachment, AttachmentChunk.attachment_id == Attachment.id)
        .where(Attachment.project_id == project_id)
        .where(
            or_(
                Attachment.pinned.is_(True),
                Attachment.id.in_(include_file_ids) if include_file_ids else False,
            )
        )
        .order_by(
            Attachment.created_at.asc(),
            AttachmentChunk.attachment_id,
            AttachmentChunk.chunk_index.asc(),
        )
    )
    for chunk, fname in (await db.execute(pinned_stmt)).all():
        if chunk.id in seen:
            continue
        seen.add(chunk.id)
        ordered.append(
            RetrievedExcerpt(
                attachment_id=chunk.attachment_id,
                filename=fname,
                chunk_index=chunk.chunk_index,
                token_est=chunk.token_est,
                pinned=True,
                matched=False,
                content=chunk.content,
            )
        )

    # 2. Lexical matches for the current query (ts_rank_cd), project-scoped.
    if query and query.strip():
        tsq = func.plainto_tsquery("english", query)
        rank = func.ts_rank_cd(AttachmentChunk.search_tsv, tsq)
        ranked_stmt = (
            select(AttachmentChunk, Attachment.filename, rank.label("rank"))
            .join(Attachment, AttachmentChunk.attachment_id == Attachment.id)
            .where(Attachment.project_id == project_id)
            .where(AttachmentChunk.search_tsv.op("@@")(tsq))
            .order_by(
                rank.desc(),
                AttachmentChunk.attachment_id,
                AttachmentChunk.chunk_index.asc(),
            )
            .limit(get_settings().file_retrieval_candidate_limit)
        )
        for chunk, fname, rank_val in (await db.execute(ranked_stmt)).all():
            if chunk.id in seen:
                continue
            seen.add(chunk.id)
            ordered.append(
                RetrievedExcerpt(
                    attachment_id=chunk.attachment_id,
                    filename=fname,
                    chunk_index=chunk.chunk_index,
                    token_est=chunk.token_est,
                    pinned=False,
                    matched=True,
                    rank=float(rank_val) if rank_val is not None else None,
                    content=chunk.content,
                )
            )

    # 3. Greedy fit to the token budget (pinned already lead the list). Each block
    #    is costed with its "[File: … | Chunk N]" label included.
    included: list[RetrievedExcerpt] = []
    dropped: list[RetrievedExcerpt] = []
    rendered: list[str] = []
    used = 0
    for exc in ordered:
        block = _format_excerpt(exc.filename, exc.chunk_index, exc.content)
        cost = estimate_tokens(block)
        if used + cost > token_budget:
            dropped.append(exc)
            continue
        used += cost
        rendered.append(block)
        included.append(exc)

    return RetrievalResult("\n\n".join(rendered), included, dropped)
