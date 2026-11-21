"""baseline - Phase 1 migration harness

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-21

Establishes the Alembic migration harness and the ``alembic_version`` table.
No domain tables exist yet in Phase 1 (users / projects / conversations arrive
in Phase 2+), so ``upgrade()`` / ``downgrade()`` are intentionally empty. This
lets ``alembic upgrade head`` and ``alembic downgrade base`` round-trip cleanly,
satisfying the Phase 1 testing requirement.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
