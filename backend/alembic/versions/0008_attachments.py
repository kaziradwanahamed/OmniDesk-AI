"""attachments + attachment_chunks

Revision ID: 0008_attachments
Revises: 0007_message_groups
Create Date: 2026-11-22

Phase 9 schema per Blueprint Ch. 22. Project-scoped uploaded documents ground any
model in real specifications without re-pasting them each turn.

- ``attachments``: one row per stored file. ``storage_key`` is a server-generated
  UUID filename on disk (user filenames are never trusted on disk); ``sha256`` is
  unique per project for clean deduplication; ``extraction_status`` records how
  text extraction went (extracted / empty / encrypted / failed) without crashing.
- ``attachment_chunks``: deterministic overlapping excerpts. ``search_tsv`` is a
  STORED generated column (``to_tsvector('english', content)``) with a GIN index,
  so Phase-9 lexical retrieval (``ts_rank_cd``) needs no extra infrastructure and
  no manual trigger to stay in sync.

Retrieval stays on native PostgreSQL full-text search + explicit user pins; no
vector DB / embedding dependency is added (blueprint: add pgvector only if lexical
search proves insufficient).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_attachments"
down_revision: Union[str, None] = "0007_message_groups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("extension", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column(
            "extraction_status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column(
            "chunk_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "pinned", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "project_id", "sha256", name="uq_attachment_project_sha256"
        ),
    )
    op.create_index("ix_attachments_project", "attachments", ["project_id"])

    op.create_table(
        "attachment_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attachment_id",
            sa.Uuid(),
            sa.ForeignKey("attachments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_est", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "attachment_id", "chunk_index", name="uq_chunk_attachment_index"
        ),
    )
    op.create_index(
        "ix_attachment_chunks_attachment", "attachment_chunks", ["attachment_id"]
    )
    op.create_index(
        "ix_attachment_chunks_search_tsv",
        "attachment_chunks",
        ["search_tsv"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attachment_chunks_search_tsv", table_name="attachment_chunks"
    )
    op.drop_index(
        "ix_attachment_chunks_attachment", table_name="attachment_chunks"
    )
    op.drop_table("attachment_chunks")
    op.drop_index("ix_attachments_project", table_name="attachments")
    op.drop_table("attachments")
