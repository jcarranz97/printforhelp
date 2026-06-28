"""Pydantic request/response models for the collection centers domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.users.constants import UserRole

from .constants import CollectionCenterRole, CollectionCenterStatus


def _validate_location_url(value: str | None) -> str | None:
    """Normalize and validate an optional map link (e.g. Google Maps).

    Empty strings collapse to ``None``; a non-empty value must be an
    absolute ``http(s)`` URL so the frontend can safely render it as a
    hyperlink.
    """
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if not trimmed.startswith(("http://", "https://")):
        raise ValueError("location_url must start with http:// or https://")
    return trimmed


class CollectionCenterResponse(BaseModel):
    """Public representation of a collection center."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    country: str
    city: str
    contact: str
    location_url: str | None
    opening_hours: str | None
    description: str | None
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
    location_url: str | None = None
    opening_hours: str | None = None
    description: str | None = None
    owner_organization_id: UUID | None = None

    _normalize_location_url = field_validator("location_url")(_validate_location_url)


class CollectionCenterUpdate(BaseModel):
    """Edit a center's mutable fields (effective member or mod/admin)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1, max_length=80)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    contact: str | None = Field(default=None, min_length=1, max_length=255)
    location_url: str | None = None
    opening_hours: str | None = None
    description: str | None = None

    _normalize_location_url = field_validator("location_url")(_validate_location_url)


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
