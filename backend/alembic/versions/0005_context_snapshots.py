"""context_snapshots

Revision ID: 0005_context_snapshots
Revises: 0004_provider_configs_usage
Create Date: 2026-11-21

Phase 6 schema per Blueprint Chapter 18: an auditable, per-turn snapshot of the
exact token-budgeted context the ContextBuilder assembled and sent. This is the
only new table in Phase 6 — project_decisions/project_tasks already exist (0002)
and messages/conversations already carry the switching + snapshot columns (0003).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_context_snapshots"
down_revision: Union[str, None] = "0004_provider_configs_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_provider", sa.Text(), nullable=False),
        sa.Column("target_model_id", sa.Text(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("estimated_input_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "included_layers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "omitted_items_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_context_snapshots_conversation",
        "context_snapshots",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_context_snapshots_conversation", table_name="context_snapshots")
    op.drop_table("context_snapshots")
