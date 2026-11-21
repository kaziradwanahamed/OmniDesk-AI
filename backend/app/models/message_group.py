"""Message group ORM model (Phase 8: multi-model parallel responses).

A group ties the parallel responses to one prompt together. ``selected_message_id``
is the response (or synthesis) that feeds future context; every response is still
stored independently in ``messages`` with its own provider/model/usage. Links are
value-based (no FK to messages) to keep the migration additive.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageGroup(Base):
    __tablename__ = "message_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_message_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    selected_message_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    kind: Mapped[str] = mapped_column(
        Text, nullable=False, default="parallel", server_default="parallel"
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship()

    __table_args__ = (
        Index("ix_message_groups_conversation", "conversation_id"),
    )
