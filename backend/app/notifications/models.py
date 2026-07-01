"""SQLAlchemy models for watch subscriptions and notifications.

Both are polymorphic over ``entity_type`` + ``entity_id`` (mirroring the
activity log) so a single pair of tables covers every watchable domain:
collection centers, shipments, resources, and requests.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel


class Watch(BaseModel):
    """A user's subscription to a polymorphic entity (FR-watch).

    Unwatch is a soft delete (``active = False``); re-watching reactivates
    the same row, so the partial unique index keeps at most one active
    subscription per (user, entity).
    """

    __tablename__ = "watches"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_watches_active",
            "user_id",
            "entity_type",
            "entity_id",
            unique=True,
            postgresql_where=text("active"),
        ),
        Index("ix_watches_entity", "entity_type", "entity_id"),
    )


class Notification(BaseModel):
    """A single in-app notification delivered to one recipient.

    ``payload`` caches the display ``title`` and frontend ``link`` resolved
    at creation so the list reads in O(1) (and the nested shipment URL,
    which needs its parent center, is captured up front).
    """

    __tablename__ = "notifications"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    comment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Future email opt-in: set when an email digest has shipped this row.
    # Unused in v1 (in-app only).
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "ix_notifications_recipient_read_created",
            "recipient_user_id",
            "read_at",
            "created_at",
        ),
    )
