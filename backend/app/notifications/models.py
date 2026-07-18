"""SQLAlchemy models for watch subscriptions and notifications.

Both are polymorphic over ``entity_type`` + ``entity_id`` (mirroring the
activity log) so a single pair of tables covers every watchable domain:
collection centers, shipments, resources, and requests.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
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
    # Legacy per-row email-digest hook. Superseded by the
    # ``NotificationEmailOutbox`` table (email is decoupled from the in-app
    # row so it ships even when the in-app channel is off); kept for a future
    # digest that may batch these. Unused today.
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "ix_notifications_recipient_read_created",
            "recipient_user_id",
            "read_at",
            "created_at",
        ),
    )


class NotificationPreference(BaseModel):
    """A user's channel choice for one notification category.

    One row per ``(user, category)``: ``in_app_enabled`` gates the in-app
    ``Notification`` and ``email_enabled`` gates the outbox email. An absent
    row means "use the category default" (``CATEGORY_DEFAULTS``), so a user
    who never opened the settings page still gets the opt-out defaults.
    """

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index(
            "uq_notification_preferences_active",
            "user_id",
            "category",
            unique=True,
            postgresql_where=text("active"),
        ),
    )


class NotificationEmailOutbox(BaseModel):
    """A pending (or sent) notification email — the transactional outbox.

    Written in the same transaction as the event that produced it (so it is
    durable and atomic), then drained by a background worker that sends via
    SMTP and stamps ``sent_at``. Kept self-contained (no FK to a
    ``Notification``) so an email still ships when the recipient turned the
    in-app channel off. ``payload`` mirrors the notification's cached
    ``title`` / ``link`` / ``anchor`` so the worker can render without extra
    lookups.
    """

    __tablename__ = "notification_email_outbox"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    comment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        # The drain scans unsent rows oldest-first; this index keeps that
        # claim query (``sent_at IS NULL AND active``) cheap.
        Index("ix_notification_email_outbox_pending", "sent_at", "active"),
    )
