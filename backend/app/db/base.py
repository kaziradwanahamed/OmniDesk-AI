"""Declarative base for all SQLAlchemy ORM models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Domain models (Phase 2+) subclass this."""

    pass
