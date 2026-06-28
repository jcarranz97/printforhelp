"""Pydantic request/response models for the requests domain."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .constants import RequestStatus


class RequestItemProgress(BaseModel):
    """Aggregated Contribution progress for a RequestItem (FR-062/063)."""

    target_quantity: int | None
    claimed_quantity: int
    at_center_quantity: int
    committed_quantity: int
    remaining: int | None


class RequestItemCreate(BaseModel):
    """A line item to add to a Request (FR-120)."""

    part_id: UUID
    quantity: int | None = Field(default=None, gt=0)
    description: str | None = None
    deadline: date | None = None


class RequestItemResponse(BaseModel):
    """A RequestItem with its live progress summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID
    part_id: UUID
    quantity: int | None
    description: str | None
    deadline: date | None
    status: RequestStatus
    closed_reason: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
    progress: RequestItemProgress


class RequestCreate(BaseModel):
    """Create a Request with at least one item (FR-038 / FR-119)."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    deadline: date | None = None
    preferred_collection_center_ids: list[UUID] = Field(default_factory=list)
    owner_organization_id: UUID | None = None
    items: list[RequestItemCreate] = Field(min_length=1)


class RequestUpdate(BaseModel):
    """Edit campaign-level metadata while the Request is open (FR-042)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    deadline: date | None = None
    preferred_collection_center_ids: list[UUID] | None = None


class CloseRequest(BaseModel):
    """Optional reason payload for closing a Request or item (FR-043)."""

    reason: str | None = None


class RequestResponse(BaseModel):
    """Campaign-level Request without its items (list view)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    deadline: date | None
    requester_user_id: UUID | None
    requester_organization_id: UUID | None
    created_by_id: UUID
    preferred_collection_center_ids: list[UUID]
    status: RequestStatus
    closed_reason: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class RequestDetailResponse(RequestResponse):
    """A Request with its embedded items + per-item progress."""

    items: list[RequestItemResponse]
