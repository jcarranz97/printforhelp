"""SQLAlchemy models for the public activity log and comments.

Both tables are polymorphic over ``entity_type`` + ``entity_id`` so a
single pair of tables covers every commentable domain. Unlike the
internal ``audit_log`` (moderation trail, NFR-008), these rows are
**publicly readable** — they power the community-facing timeline on a
Collection Center or Shipment.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel


class ActivityLog(BaseModel):
    """Append-only, publicly readable record of lifecycle events."""

    __tablename__ = "activity_log"

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    changes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index(
            "ix_activity_log_entity_created",
            "entity_type",
            "entity_id",
            "created_at",
        ),
    )


class Comment(BaseModel):
    """User-authored, Markdown comment attached polymorphically (FR-131).

    Comments support one level of Instagram-style replies. A reply carries
    ``parent_comment_id`` pointing at the **top-level** comment it belongs to;
    the service re-roots a reply-to-a-reply onto that same top-level comment so
    a thread never nests deeper than one level (see ``create_comment``).
    """

    __tablename__ = "comments"

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # Null for a top-level comment; the id of the top-level comment for a reply.
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "ix_comments_entity_created",
            "entity_type",
            "entity_id",
            "created_at",
        ),
        Index(
            "ix_comments_parent_created",
            "parent_comment_id",
            "created_at",
        ),
    )
