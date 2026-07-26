"""Pydantic request/response models for the shipments domain."""

from datetime import date, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import ShipmentStatus


class ShipmentResponse(BaseModel):
    """Public representation of a Collection Center shipment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_center_id: UUID
    shipment_date: date
    status: ShipmentStatus
    destination: str | None
    # Set when the next stop is another Collection Center — this box is a
    # relay hop rather than a final delivery.
    destination_collection_center_id: UUID | None
    description: str | None
    # The QR taped to the box; resolves on the public ``/track/{token}`` page.
    tracking_token: str
    dispatched_at: datetime | None
    arrived_at: datetime | None
    arrived_by_id: UUID | None
    created_by_id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime


class ShipmentCreate(BaseModel):
    """Create a shipment (effective member or maintainer/admin, FR-129)."""

    shipment_date: date
    status: ShipmentStatus = ShipmentStatus.RECEIVING
    destination: str | None = Field(default=None, max_length=255)
    destination_collection_center_id: UUID | None = None
    description: str | None = None


class ShipmentUpdate(BaseModel):
    """Edit a shipment, including its status (FR-129).

    Every field is optional; only the keys present in the request are
    applied. Setting ``status`` advances the shipment through its lifecycle
    (see :data:`~app.shipments.constants.SHIPMENT_TRANSITIONS`).
    """

    shipment_date: date | None = None
    status: ShipmentStatus | None = None
    destination: str | None = Field(default=None, max_length=255)
    destination_collection_center_id: UUID | None = None
    description: str | None = None


class MyShipmentResponse(ShipmentResponse):
    """A shipment as it appears in the caller's own cross-center list.

    Carries the owning center's name so the list can group by center without a
    lookup per row, and the package count so a member can see at a glance which
    boxes are worth opening.
    """

    collection_center_name: str
    destination_collection_center_name: str | None = None
    package_count: int = 0


class ContentKind(StrEnum):
    """What a manifest line holds."""

    # One maker's Contribution, with all of its units.
    PACKAGE = "package"
    # Another shipment, nested whole (the relay case).
    BOX = "box"


class ShipmentContentEntry(BaseModel):
    """One line of a shipment's manifest, redacted for the viewer.

    A box is public but its contents are not necessarily: a package whose
    tracking group is ``private`` or ``group``-tier must not become readable
    just because someone photographed the box. Such a line comes back with
    ``redacted = True`` and every identifying field blanked — it is counted,
    never described. See ``service.list_contents``.
    """

    id: UUID
    kind: ContentKind
    redacted: bool = False

    # --- package lines (all None when redacted) --- #
    tracking_group_id: UUID | None = None
    tracking_token: str | None = None
    resource_name: str | None = None
    quantity: int | None = None
    contribution_status: str | None = None
    maker_username: str | None = None
    # Enough to render the maker the same way the commitments list does.
    maker_full_name: str | None = None
    maker_avatar_url: str | None = None
    maker_avatar_crop_x: float = 0
    maker_avatar_crop_y: float = 0
    maker_avatar_crop_w: float = 100
    maker_avatar_crop_h: float = 100

    # --- box lines --- #
    child_shipment_id: UUID | None = None
    child_status: ShipmentStatus | None = None
    child_destination: str | None = None
    child_tracking_token: str | None = None
    # How many packages ride inside the nested box, at any depth.
    child_package_count: int | None = None

    added_at: datetime


class ShipmentContentsResponse(BaseModel):
    """A shipment's manifest plus the totals a scanner needs at a glance."""

    shipment_id: UUID
    # Direct manifest lines (packages + nested boxes), not counting deeper ones.
    contents_total: int
    # Nested boxes among them.
    child_count: int
    # Packages at any depth, including inside nested boxes.
    package_count: int
    # Units the viewer is allowed to see, summed across visible packages only,
    # so the total can never be differenced against ``hidden_count`` to
    # reconstruct a private quantity.
    units_total: int
    # Packages withheld from this viewer. Reported as a bare count so the box
    # still adds up without naming what is inside.
    hidden_count: int
    entries: list[ShipmentContentEntry]
    # Whether the caller may pack and unpack this box (drives the UI only; the
    # write paths re-check it themselves, NFR-006).
    can_manage_contents: bool = False


class ShipmentContentResponse(BaseModel):
    """The raw manifest row, echoed back after packing something."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    tracking_group_id: UUID | None
    child_shipment_id: UUID | None
    added_by_id: UUID
    active: bool
    created_at: datetime


class ShipmentArrivalResponse(BaseModel):
    """The outcome of signing for a box (FR-143).

    The skip counts are reported rather than hidden so the receiving team can
    tell "everything was already receipted upstream" from "one package has no
    drop-off center and needs a human".
    """

    shipment: ShipmentResponse
    received: int
    skipped_already: int
    skipped_no_center: int
    packages_total: int


class ShipmentContentCreate(BaseModel):
    """Pack something into a shipment (FR-138).

    Exactly one of the three must be given. ``tracking_token`` is the one the
    staff actually use: they scan whatever QR is on the thing in their hand and
    paste it. It resolves a unit token, a package token, or another box's token
    — scanning any single unit packs the whole package it belongs to, because
    packages are what get packed, not loose units.
    """

    tracking_token: str | None = Field(default=None, max_length=512)
    tracking_group_id: UUID | None = None
    child_shipment_id: UUID | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self) -> Self:
        given = [
            self.tracking_token,
            self.tracking_group_id,
            self.child_shipment_id,
        ]
        if sum(value is not None for value in given) != 1:
            message = (
                "Provide exactly one of tracking_token, tracking_group_id, "
                "or child_shipment_id."
            )
            raise ValueError(message)
        return self
