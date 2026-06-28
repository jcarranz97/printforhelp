"""Declarative base and the shared BaseModel mixin.

Every ORM model inherits from :class:`BaseModel`, which supplies the UUID
primary key, creation/update timestamps, and the soft-delete ``active``
flag mandated by NFR-012.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


class BaseModel(Base):
    """Abstract base supplying id, timestamps, and the soft-delete flag."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
