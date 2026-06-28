"""SQLAlchemy model for Collection Center shipments."""

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import ShipmentStatus


class Shipment(BaseModel):
    """A planned dispatch of aid from a Collection Center (FR-127).

    Shipments are owned by their Collection Center; the per-center effective
    members (owner, contributors, owning-org members) plus maintainers and
    admins manage them. They are always publicly readable so the community
    knows the deadlines by which to drop off their printed parts.
    """

    __tablename__ = "shipments"

    collection_center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collection_centers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shipment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(
            ShipmentStatus,
            name="shipment_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ShipmentStatus.RECEIVING,
        index=True,
    )
    destination: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
