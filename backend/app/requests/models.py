"""SQLAlchemy models for Requests (campaigns) and their RequestItems."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
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

from .constants import RequestStatus


class Request(BaseModel):
    """A campaign-level container for one or more RequestItems (FR-038).

    The requester is polymorphic (FR-039): either a User or an Organization,
    with a CHECK enforcing exactly one non-null. ``created_by_id`` records
    the human who first created it (immutable attribution).
    """

    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint(
            "(requester_user_id IS NOT NULL AND requester_organization_id IS NULL) "
            "OR (requester_user_id IS NULL "
            "AND requester_organization_id IS NOT NULL)",
            name="requests_one_requester",
        ),
        CheckConstraint(
            "(status = 'open' AND closed_at IS NULL) OR "
            "(status IN ('fulfilled', 'closed') AND closed_at IS NOT NULL)",
            name="request_closed_consistency",
        ),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    deadline: Mapped[date | None] = mapped_column(Date)
    requester_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    requester_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    preferred_collection_center_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    status: Mapped[RequestStatus] = mapped_column(
        Enum(
            RequestStatus,
            name="request_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=RequestStatus.OPEN,
        index=True,
    )
    closed_reason: Mapped[str | None] = mapped_column(Text)
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequestItem(BaseModel):
    """A single Resource with a target quantity within a Request (FR-119/120)."""

    __tablename__ = "request_items"
    __table_args__ = (
        CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="request_item_quantity_positive",
        ),
        CheckConstraint(
            "(status = 'open' AND closed_at IS NULL) OR "
            "(status IN ('fulfilled', 'closed') AND closed_at IS NOT NULL)",
            name="request_item_closed_consistency",
        ),
        # A stable, per-Request sequential number (1, 2, ...) so duplicate
        # Resources are distinguishable and get short, shareable item URLs.
        # Numbers are never reused (assigned as max+1), so a removed item's
        # number will not collide with a shared link.
        UniqueConstraint("request_id", "item_number", name="uq_request_item_number"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_number: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id"), nullable=False, index=True
    )
    quantity: Mapped[int | None] = mapped_column(Integer)
    # The unit of measure chosen for this item's quantity (e.g. "litros").
    # Seeded from the Resource's suggested ``units`` but freely editable by the
    # requester; NULL means countable pieces (the default for 3D prints).
    unit: Mapped[str | None] = mapped_column(String(32))
    # An optional per-item narrowing of the parent Request's preferred drop-off
    # centers: a subset chosen when this specific item is only needed at some of
    # them. Empty means "all of the Request's preferred centers apply". Always
    # resolved against the Request's current list at read time.
    preferred_collection_center_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    description: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(
            RequestStatus,
            name="request_status",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
        default=RequestStatus.OPEN,
        index=True,
    )
    closed_reason: Mapped[str | None] = mapped_column(Text)
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
