"""Conversation and Message ORM models (provider-independent canonical store)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    active_provider: Mapped[str | None] = mapped_column(Text, default=None)
    active_model_id: Mapped[str | None] = mapped_column(Text, default=None)
    auto_fallback_enabled: Mapped[bool] = mapped_column(
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

    project: Mapped["Project"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conversations_project_updated", "project_id", "updated_at"),
    )


class Message(Base):
    """Canonical, provider-independent message row.

    Phases 4–6 add streaming, usage records, context snapshots, and multi-model
    groups; the nullable columns here (provider/model/usage/latency/group/
    snapshot/metadata) exist now so those phases are additive, not rewrites.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # user|assistant|system_event
    content: Mapped[str] = mapped_column(Text, nullable=False)

    provider: Mapped[str | None] = mapped_column(Text, default=None)
    model_id: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="completed", server_default="completed"
    )  # completed|streaming|failed
    error_code: Mapped[str | None] = mapped_column(Text, default=None)

    # Correlation to future features (no FK yet; tables arrive in later phases).
    group_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    context_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    # Usage / latency metadata (nullable — never fabricated).
    input_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    output_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    total_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    provider_request_id: Mapped[str | None] = mapped_column(Text, default=None)

    metadata_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence_no", name="uq_message_conv_seq"),
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
    )
