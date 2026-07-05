"""SQLAlchemy models for the item-tracking (QR provenance) domain.

A :class:`TrackingGroup` is the tracking handle for one Contribution; it
owns one :class:`TrackingItem` per printed unit. Both carry an unguessable
``tracking_token`` that appears in the public ``/track/{token}`` URL. Anyone
allowed to view a token (per :class:`TrackingGroup.visibility`) can append a
:class:`TrackingRecord`.
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import TrackingVisibility


class TrackingGroup(BaseModel):
    """Tracking handle for one Contribution (1:1)."""

    __tablename__ = "tracking_groups"

    contribution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contributions.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    tracking_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    visibility: Mapped[TrackingVisibility] = mapped_column(
        Enum(
            TrackingVisibility,
            name="tracking_visibility",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=TrackingVisibility.PUBLIC,
    )


class ContributorMessage(BaseModel):
    """A reusable maker note ("template") saved by a user for label prints.

    Linked to the **user**, not a tracking, so the same message can be picked
    and reused across every tracking they manage (GitHub "saved replies"
    style). Soft-deleted like everything else.
    """

    __tablename__ = "contributor_messages"

    # No cascade from users (FR-013): saved templates outlive deactivation.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)


class TrackingItem(BaseModel):
    """A single printed unit within a group, with its own QR token."""

    __tablename__ = "tracking_items"
    __table_args__ = (
        UniqueConstraint("group_id", "sequence", name="tracking_item_group_sequence"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracking_groups.id"),
        nullable=False,
        index=True,
    )
    tracking_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    # 1-based position within the group (unit 1..quantity).
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)


class TrackingGroupMember(BaseModel):
    """A named user granted read access under the ``group`` visibility tier."""

    __tablename__ = "tracking_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="tracking_group_member_unique"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracking_groups.id"),
        nullable=False,
        index=True,
    )
    # No cascade from users (FR-013): membership rows outlive user deactivation.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )


class TrackingRecord(BaseModel):
    """A timestamped update on a tracking group or item (polymorphic).

    Exactly one of ``tracking_group_id`` / ``tracking_item_id`` is set. The
    ``author_user_id`` is recorded whenever a logged-in user posts (so a scan
    can be traced if ever needed) even when ``display_anonymous`` hides the
    name from the public timeline; guest posts leave it null.
    """

    __tablename__ = "tracking_records"
    __table_args__ = (
        CheckConstraint(
            "(tracking_group_id IS NOT NULL)::int "
            "+ (tracking_item_id IS NOT NULL)::int = 1",
            name="tracking_record_one_target",
        ),
    )

    tracking_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracking_groups.id"), index=True
    )
    tracking_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracking_items.id"), index=True
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    display_anonymous: Mapped[bool] = mapped_column(nullable=False, default=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
