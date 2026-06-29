"""Pydantic request/response models for the contributions domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .constants import ContributionStatus


class ContributionResponse(BaseModel):
    """Representation of a maker Contribution."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_item_id: UUID
    maker_id: UUID
    collection_center_id: UUID | None
    quantity: int
    notes: str | None
    status: ContributionStatus
    claimed_at: datetime
    prepared_at: datetime | None
    delivered_at: datetime | None
    received_at: datetime | None
    received_by_id: UUID | None
    auto_received: bool
    released_at: datetime | None
    released_reason: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class MyContributionResponse(ContributionResponse):
    """A maker's Contribution enriched with its Resource and Request context."""

    request_id: UUID
    request_title: str
    resource_id: UUID
    resource_name: str


class ContributionCreate(BaseModel):
    """Claim a quantity of a RequestItem (FR-050).

    The drop-off ``collection_center_id`` is optional at claim time so makers
    can commit to print before they have a center; it can be set later.
    """

    request_item_id: UUID
    quantity: int = Field(gt=0)
    collection_center_id: UUID | None = None
    notes: str | None = None


class ContributionUpdate(BaseModel):
    """Edit a claimed Contribution.

    Quantity/notes are editable only while ``claimed`` (FR-057); the
    ``collection_center_id`` may also be set while ``prepared`` (so a maker
    can add a drop-off center before delivering).
    """

    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = None
    collection_center_id: UUID | None = None
