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
    collection_center_id: UUID
    quantity: int
    notes: str | None
    status: ContributionStatus
    claimed_at: datetime
    printed_at: datetime | None
    delivered_at: datetime | None
    received_at: datetime | None
    received_by_id: UUID | None
    auto_received: bool
    released_at: datetime | None
    released_reason: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class ContributionCreate(BaseModel):
    """Claim a quantity of a RequestItem at a Collection Center (FR-050)."""

    request_item_id: UUID
    quantity: int = Field(gt=0)
    collection_center_id: UUID
    notes: str | None = None


class ContributionUpdate(BaseModel):
    """Edit quantity/notes while the Contribution is still claimed (FR-057)."""

    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = None
