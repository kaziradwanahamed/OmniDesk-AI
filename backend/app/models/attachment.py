"""Project file attachments + their retrievable text chunks (Phase 9).

Uploaded project documents are stored on disk under a server-generated UUID key
(``storage_key``) — user filenames are never trusted on disk. Extracted text is
split into deterministic overlapping :class:`AttachmentChunk` rows whose
``search_tsv`` is a STORED generated ``tsvector`` with a GIN index, powering
lexical ``ts_rank_cd`` retrieval into ContextBuilder Layer 5 with no extra
infrastructure. Canonical files/chunks are never mutated by context assembly.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Original (sanitized) display name — basename only, never a disk path.
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    extension: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    # Server-generated UUID filename on disk (relative to the upload root).
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | extracted | empty | encrypted | failed
    extraction_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default="pending"
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, default=None)
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Explicitly pin a key document into L5 on every turn of the project.
    pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project: Mapped["Project"] = relationship(back_populates="attachments")
    chunks: Mapped[list["AttachmentChunk"]] = relationship(
        back_populates="attachment",
        cascade="all, delete-orphan",
        order_by="AttachmentChunk.chunk_index",
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id", "sha256", name="uq_attachment_project_sha256"
        ),
    )


class AttachmentChunk(Base):
    __tablename__ = "attachment_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_est: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    # Line offsets for text/code; page offsets for PDFs (the other pair is NULL).
    start_line: Mapped[int | None] = mapped_column(Integer, default=None)
    end_line: Mapped[int | None] = mapped_column(Integer, default=None)
    page_start: Mapped[int | None] = mapped_column(Integer, default=None)
    page_end: Mapped[int | None] = mapped_column(Integer, default=None)
    # STORED generated tsvector kept in sync with ``content`` by PostgreSQL.
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    attachment: Mapped["Attachment"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint(
            "attachment_id", "chunk_index", name="uq_chunk_attachment_index"
        ),
        Index(
            "ix_attachment_chunks_search_tsv",
            "search_tsv",
            postgresql_using="gin",
        ),
    )
