"""Provider configuration (encrypted keys) and usage ledger ORM models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    # Encrypted ciphertext (never the raw key); nullable so a config can exist
    # with models enabled but a deleted key.
    encrypted_api_key: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    key_hint: Mapped[str | None] = mapped_column(Text, default=None)
    enabled_models: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    pricing_overrides_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    is_enabled: Mapped[bool] = mapped_column(
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

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_provider_config_user_provider"),
    )


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    message_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str | None] = mapped_column(Text, default=None)
    input_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    output_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    total_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    provider_request_id: Mapped[str | None] = mapped_column(Text, default=None)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_usage_user_created", "user_id", "created_at"),
        Index("ix_usage_user_provider", "user_id", "provider"),
    )
