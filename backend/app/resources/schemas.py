"""Pydantic request/response models for the resources domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import ResourceCategory, ResourceStatus


def _validate_http_url(value: str | None) -> str | None:
    """Normalize and validate an optional media URL.

    Empty strings collapse to ``None``. A non-empty value must be either an
    absolute ``http(s)`` URL (a pasted external link) or a site-relative
    path such as ``/media/files/x.stl`` — the form returned by our own
    uploads when ``MEDIA_BASE_URL`` is unset. Protocol-relative ``//host``
    values are rejected since they point at an external origin. The
    ``source_url``-is-required-for-print_3d rule lives in the service
    layer (it depends on the resource's category and, for updates, on the
    existing row), not here.
    """
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    is_absolute = trimmed.startswith(("http://", "https://"))
    is_site_relative = trimmed.startswith("/") and not trimmed.startswith("//")
    if not (is_absolute or is_site_relative):
        raise ValueError("URL must be an http(s) URL or a site-relative path")
    return trimmed


def _normalize_units(units: list[str] | None) -> list[str] | None:
    """Trim, drop blanks, and de-duplicate units case-insensitively.

    Keeps the first-seen casing and order so the suggested units stay unique
    and readable (mirrors the maker-tag normalization).
    """
    if units is None:
        return None
    seen: set[str] = set()
    result: list[str] = []
    for raw in units:
        unit = raw.strip()
        key = unit.casefold()
        if unit and key not in seen:
            seen.add(key)
            result.append(unit)
    return result


class ResourceResponse(BaseModel):
    """Public representation of a Resource."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    category: ResourceCategory
    source_url: str | None
    image_url: str | None
    label_image_url: str | None
    units: list[str]
    tags: list[str]
    status: ResourceStatus
    featured: bool
    creator_id: UUID
    owner_user_id: UUID | None
    owner_organization_id: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime


class ResourceCreate(BaseModel):
    """Register a Resource. Owner defaults to the caller (FR-015).

    ``category`` defaults to ``print_3d`` so existing 3D-print clients
    (which never send it) keep their current behaviour, including the
    ``source_url`` requirement enforced in the service layer.
    """

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: ResourceCategory = ResourceCategory.PRINT_3D
    source_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    label_image_url: str | None = Field(default=None, max_length=500)
    units: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    owner_organization_id: UUID | None = None

    _normalize_source_url = field_validator("source_url")(_validate_http_url)
    _normalize_image_url = field_validator("image_url")(_validate_http_url)
    _normalize_label_image_url = field_validator("label_image_url")(_validate_http_url)
    _normalize_units = field_validator("units")(_normalize_units)


class ResourceUpdate(BaseModel):
    """Edit a Resource's mutable fields (effective owner)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: ResourceCategory | None = None
    source_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    label_image_url: str | None = Field(default=None, max_length=500)
    units: list[str] | None = None
    tags: list[str] | None = None
    featured: bool | None = None

    _normalize_source_url = field_validator("source_url")(_validate_http_url)
    _normalize_image_url = field_validator("image_url")(_validate_http_url)
    _normalize_label_image_url = field_validator("label_image_url")(_validate_http_url)
    _normalize_units = field_validator("units")(_normalize_units)
