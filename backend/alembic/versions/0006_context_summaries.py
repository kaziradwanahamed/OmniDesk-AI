"""context_summaries

Revision ID: 0006_context_summaries
Revises: 0005_context_snapshots
Create Date: 2026-11-21

Phase 7 schema per Blueprint Chapter 19: a rolling, versioned conversation
summary (L6). A summary is an auditable convenience layer — the original
canonical ``messages`` rows are NEVER deleted or mutated. A partial unique index
guarantees at most one active summary per conversation.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_context_summaries"
down_revision: Union[str, None] = "0005_context_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "context_summaries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("covers_up_to_sequence", sa.Integer(), nullable=False),
        sa.Column(
            "covered_message_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "estimated_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column(
            "user_edited", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
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
    )
    op.create_index(
        "ix_context_summaries_conversation",
        "context_summaries",
        ["conversation_id", "version"],
    )
    op.create_index(
        "uq_active_summary_per_conversation",
        "context_summaries",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_active_summary_per_conversation", table_name="context_summaries"
    )
    op.drop_index(
        "ix_context_summaries_conversation", table_name="context_summaries"
    )
    op.drop_table("context_summaries")
