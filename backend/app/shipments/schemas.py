"""Pydantic request/response models for the shipments domain."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .constants import ShipmentStatus


class ShipmentResponse(BaseModel):
    """Public representation of a Collection Center shipment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_center_id: UUID
    shipment_date: date
    status: ShipmentStatus
    destination: str | None
    description: str | None
    created_by_id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime


class ShipmentCreate(BaseModel):
    """Create a shipment (effective member or maintainer/admin, FR-129)."""

    shipment_date: date
    status: ShipmentStatus = ShipmentStatus.RECEIVING
    destination: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ShipmentUpdate(BaseModel):
    """Edit a shipment, including its status (FR-129).

    Every field is optional; only the keys present in the request are
    applied. Setting ``status`` advances the shipment through its lifecycle
    (``receiving`` / ``closed`` / ``cancelled``).
    """

    shipment_date: date | None = None
    status: ShipmentStatus | None = None
    destination: str | None = Field(default=None, max_length=255)
    description: str | None = None
