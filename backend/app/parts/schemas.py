"""Pydantic request/response models for the parts domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import PartStatus


def _validate_http_url(value: str | None) -> str | None:
    """Normalize and validate an optional absolute ``http(s)`` URL.

    Empty strings collapse to ``None``; a non-empty value must be an
    absolute ``http(s)`` URL so the frontend can render it safely.
    """
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if not trimmed.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return trimmed


def _validate_required_http_url(value: str) -> str:
    """Validate a required absolute ``http(s)`` URL (the source URL)."""
    normalized = _validate_http_url(value)
    if normalized is None:
        raise ValueError("source_url is required and must be an http(s) URL")
    return normalized


class PartResponse(BaseModel):
    """Public representation of a Part."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    source_url: str
    image_url: str | None
    tags: list[str]
    status: PartStatus
    featured: bool
    creator_id: UUID
    owner_user_id: UUID | None
    owner_organization_id: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime


class PartCreate(BaseModel):
    """Register a Part. Owner defaults to the caller (FR-015)."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    source_url: str = Field(min_length=1, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    owner_organization_id: UUID | None = None

    _normalize_source_url = field_validator("source_url")(_validate_required_http_url)
    _normalize_image_url = field_validator("image_url")(_validate_http_url)


class PartUpdate(BaseModel):
    """Edit a Part's mutable fields (effective owner)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    source_url: str | None = Field(default=None, min_length=1, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
    featured: bool | None = None

    _normalize_source_url = field_validator("source_url")(_validate_http_url)
    _normalize_image_url = field_validator("image_url")(_validate_http_url)
