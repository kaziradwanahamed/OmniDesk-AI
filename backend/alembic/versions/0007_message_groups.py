"""message_groups

Revision ID: 0007_message_groups
Revises: 0006_context_summaries
Create Date: 2026-11-21

Phase 8 schema per Blueprint Ch. 20-21: a message_group ties together the
parallel responses to a single prompt. ``selected_message_id`` marks the one
response (or synthesis) that feeds future context, preventing N-way token bloat
while every response stays canonically stored in ``messages`` (linked by
``messages.group_id``). Links are value-based (no FK to messages) so no existing
table is altered.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_message_groups"
down_revision: Union[str, None] = "0006_context_summaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_message_id", sa.Uuid(), nullable=True),
        sa.Column("selected_message_id", sa.Uuid(), nullable=True),
        sa.Column(
            "kind", sa.Text(), nullable=False, server_default="parallel"
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_message_groups_conversation", "message_groups", ["conversation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_message_groups_conversation", table_name="message_groups")
    op.drop_table("message_groups")
