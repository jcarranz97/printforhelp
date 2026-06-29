"""SQLAlchemy model for maker Contributions."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import ContributionStatus


class Contribution(BaseModel):
    """A maker's pledge to print a quantity for a RequestItem (FR-050)."""

    __tablename__ = "contributions"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="contribution_quantity_positive"),
    )

    request_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("request_items.id"),
        nullable=False,
        index=True,
    )
    maker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # Optional at claim time: makers can commit to print before they have a
    # drop-off center, and assign one later (before marking delivered).
    collection_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collection_centers.id"),
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ContributionStatus] = mapped_column(
        Enum(
            ContributionStatus,
            name="contribution_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ContributionStatus.CLAIMED,
        index=True,
    )
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    auto_received: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_reason: Mapped[str | None] = mapped_column(String(64))
