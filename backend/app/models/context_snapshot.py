"""Context snapshot ORM model: a per-turn audit of the assembled context package.

Every send/stream turn records exactly which layers were included, the estimated
input-token count, the active token budget, and which items were trimmed/omitted.
This powers the "Context Included" inspector so the context sent is fully auditable.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class ContextSnapshot(Base):
    __tablename__ = "context_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_provider: Mapped[str] = mapped_column(Text, nullable=False)
    target_model_id: Mapped[str] = mapped_column(Text, nullable=False)
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # Python attribute names map to the *_json DB columns (blueprint column names).
    included_layers: Mapped[list] = mapped_column(
        "included_layers_json", JSONB, nullable=False, default=list, server_default="[]"
    )
    omitted_items: Mapped[list] = mapped_column(
        "omitted_items_json", JSONB, nullable=False, default=list, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship()

    __table_args__ = (
        Index(
            "ix_context_snapshots_conversation", "conversation_id", "created_at"
        ),
    )
