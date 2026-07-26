"""SQLAlchemy models for Collection Center shipments and their manifests."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import ShipmentStatus


class Shipment(BaseModel):
    """A physical box of aid dispatched from a Collection Center (FR-127).

    Shipments are owned by their Collection Center; the per-center effective
    members (owner, contributors, owning-org members) plus maintainers and
    admins manage them. They are always publicly readable so the community
    knows the deadlines by which to drop off their printed resources.

    A shipment is also the **container** other things ride in (FR-138): its
    manifest (:class:`ShipmentContent`) holds whole Contributions and/or other
    shipments, so a relay center can nest the box it received from upstream
    inside the bigger box it sends onward. ``tracking_token`` is the QR taped
    to the outside; scanning it lands on the same ``/track/{token}`` surface as
    a package or a single unit.
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
    # Set when the next stop is itself a Collection Center — i.e. this box is a
    # **relay hop** rather than a final delivery. The free-text ``destination``
    # above stays for everything that is not a center on the platform.
    destination_collection_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        # No CASCADE: archiving a center must not erase the shipments routed
        # through it.
        ForeignKey("collection_centers.id"),
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text)
    # The scannable handle. Minted at creation so no box is ever unscannable,
    # and never reissued — it is printed on a label stuck to a physical box.
    tracking_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # No cascade from users (FR-013): who signed for the box outlives their
    # account being deactivated.
    arrived_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )


class ShipmentContent(BaseModel):
    """One manifest line: a packed Contribution, or a nested box (FR-138).

    Exactly one of ``tracking_group_id`` / ``child_shipment_id`` is set — the
    same "exactly one of" idiom as :class:`~app.tracking.models.TrackingRecord`.
    Packing at the *tracking group* level rather than the Contribution level is
    deliberate: the group is what carries the QR, so the manifest and the scan
    surface agree on what a "package" is.

    Unpacking soft-deletes the row instead of removing it, so repacking is an
    append and "which box was this in on 3 August?" stays answerable.
    """

    __tablename__ = "shipment_contents"
    __table_args__ = (
        CheckConstraint(
            "(tracking_group_id IS NOT NULL)::int "
            "+ (child_shipment_id IS NOT NULL)::int = 1",
            name="shipment_content_one_target",
        ),
        CheckConstraint(
            "child_shipment_id IS NULL OR child_shipment_id <> shipment_id",
            name="shipment_content_not_self",
        ),
        # Partial on ``active``: a package — or a box — rides in exactly one
        # *open* box at a time, which is what makes containment a forest and
        # ancestor resolution unambiguous. Retired rows may share the slot, so
        # the full history of every box a package has passed through survives.
        # A plain unique constraint would forbid ever repacking anything.
        Index(
            "shipment_content_group_active",
            "tracking_group_id",
            unique=True,
            postgresql_where=text("active AND tracking_group_id IS NOT NULL"),
        ),
        Index(
            "shipment_content_child_active",
            "child_shipment_id",
            unique=True,
            postgresql_where=text("active AND child_shipment_id IS NOT NULL"),
        ),
        Index(
            "ix_shipment_contents_shipment",
            "shipment_id",
            postgresql_where=text("active"),
        ),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False
    )
    tracking_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracking_groups.id")
    )
    child_shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipments.id")
    )
    # No cascade from users (FR-013): who packed what outlives deactivation.
    added_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    removed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
