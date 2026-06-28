"""Pydantic request/response models for the collection centers domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.users.constants import UserRole

from .constants import CollectionCenterRole, CollectionCenterStatus


class CollectionCenterResponse(BaseModel):
    """Public representation of a collection center."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    country: str
    city: str
    contact: str
    opening_hours: str | None
    notes: str | None
    verified: bool
    registered_by_id: UUID
    verified_by_id: UUID | None
    owner_user_id: UUID | None
    owner_organization_id: UUID | None
    status: CollectionCenterStatus
    active: bool
    created_at: datetime
    updated_at: datetime


class CollectionCenterCreate(BaseModel):
    """Create a collection center. Owner defaults to the caller (FR-083)."""

    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1)
    country: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=1, max_length=255)
    opening_hours: str | None = None
    notes: str | None = None
    owner_organization_id: UUID | None = None


class CollectionCenterUpdate(BaseModel):
    """Edit a center's mutable fields (effective member or mod/admin)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1, max_length=80)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    contact: str | None = Field(default=None, min_length=1, max_length=255)
    opening_hours: str | None = None
    notes: str | None = None


class ToggleStatus(BaseModel):
    """Set a center's operational status (effective member, FR-078)."""

    status: CollectionCenterStatus


class RevokeVerification(BaseModel):
    """Reason payload for revoking verification."""

    reason: str | None = None


class ContributorResponse(BaseModel):
    """A single per-center contributor row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_center_id: UUID
    user_id: UUID
    username: str
    user_role: UserRole
    role: CollectionCenterRole
    active: bool
    created_at: datetime


class AddContributor(BaseModel):
    """Add an existing user as a per-center contributor (FR-084)."""

    username: str = Field(min_length=1, max_length=64)
