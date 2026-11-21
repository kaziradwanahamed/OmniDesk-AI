"""provider_configs & usage_records

Revision ID: 0004_provider_configs_usage
Revises: 0003_conversations_messages
Create Date: 2026-11-21

Phase 4 schema per Blueprint Chapter 9: encrypted per-user provider keys and a
verified usage ledger. API keys are stored only as ciphertext (BYTEA).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_provider_configs_usage"
down_revision: Union[str, None] = "0003_conversations_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("encrypted_api_key", sa.LargeBinary(), nullable=True),
        sa.Column("key_hint", sa.Text(), nullable=True),
        sa.Column(
            "enabled_models",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "pricing_overrides_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
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
            "user_id", "provider", name="uq_provider_config_user_provider"
        ),
    )
    op.create_index("ix_provider_configs_user_id", "provider_configs", ["user_id"])

    op.create_table(
        "usage_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_request_id", sa.Text(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_usage_user_created", "usage_records", ["user_id", "created_at"])
    op.create_index("ix_usage_user_provider", "usage_records", ["user_id", "provider"])


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_table("provider_configs")
