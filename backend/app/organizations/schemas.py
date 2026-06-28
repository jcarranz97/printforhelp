"""Pydantic request/response models for the organizations domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.users.constants import UserRole

from .constants import OrganizationRole, OrganizationStatus


class OrganizationResponse(BaseModel):
    """Public representation of an organization."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    contact: str
    website: str | None
    country: str
    verified: bool
    registered_by_id: UUID
    verified_by_id: UUID | None
    status: OrganizationStatus
    active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    """Create an organization. The caller becomes its owner (FR-095)."""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    contact: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    country: str = Field(min_length=1, max_length=80)


class OrganizationUpdate(BaseModel):
    """Edit an organization's mutable fields (owner / maintainer / admin)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    contact: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, min_length=1, max_length=80)


class RevokeVerification(BaseModel):
    """Reason payload for revoking verification."""

    reason: str | None = None


class MembershipResponse(BaseModel):
    """A single organization membership row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    username: str
    user_role: UserRole
    role: OrganizationRole
    active: bool
    created_at: datetime


class AddMember(BaseModel):
    """Add an existing user to the organization by username (FR-098)."""

    username: str = Field(min_length=1, max_length=64)


class TransferOwnership(BaseModel):
    """Transfer org ownership to an existing member (FR-101)."""

    target_user_id: UUID
