"""Conversation summary ORM model (L6: rolling, versioned older-history summary).

A summary compacts messages with ``sequence_no <= covers_up_to_sequence`` into a
structured text block. It is strictly an auditable convenience layer: the
original canonical ``messages`` rows are never deleted or mutated. At most one
row per conversation is active (enforced by a partial unique index).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class ConversationSummary(Base):
    __tablename__ = "context_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    covers_up_to_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    covered_message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Provenance: the model that generated it (null when a from-scratch user edit).
    provider: Mapped[str | None] = mapped_column(Text, default=None)
    model_id: Mapped[str | None] = mapped_column(Text, default=None)
    user_edited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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

    conversation: Mapped["Conversation"] = relationship()

    __table_args__ = (
        Index(
            "ix_context_summaries_conversation", "conversation_id", "version"
        ),
    )
