"""Pydantic request/response models for the requests domain."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import (
    MAX_REVIEW_NOTE_LENGTH,
    HelpState,
    ModerationStatus,
    RequestStatus,
)


def _validate_http_url(value: str | None) -> str | None:
    """Normalize an optional media URL (empty -> ``None``).

    Accepts an absolute ``http(s)`` URL (a pasted external link) or a
    site-relative path like ``/media/images/x.png`` — the form our own
    uploads return when ``MEDIA_BASE_URL`` is unset. Protocol-relative
    ``//host`` values are rejected as they point at an external origin.
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


class RequestItemProgress(BaseModel):
    """Aggregated Contribution progress for a RequestItem (FR-062/063)."""

    target_quantity: int | None
    claimed_quantity: int
    at_center_quantity: int
    committed_quantity: int
    remaining: int | None


def _normalize_unit(value: str | None) -> str | None:
    """Trim an optional unit label; empty collapses to ``None`` (pieces)."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class RequestItemCreate(BaseModel):
    """A line item to add to a Request (FR-120)."""

    resource_id: UUID
    quantity: int | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=32)
    description: str | None = None
    deadline: date | None = None
    # Optional per-item subset of the Request's preferred centers (empty = all).
    preferred_collection_center_ids: list[UUID] = Field(default_factory=list)

    _normalize_unit = field_validator("unit")(_normalize_unit)


class RequestItemUpdate(BaseModel):
    """Edit an item's target/unit/description/deadline or preferred centers.

    Per-item preferred centers narrow the Request's list to this item (FR-120).
    """

    quantity: int | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=32)
    description: str | None = None
    deadline: date | None = None
    # A subset of the Request's preferred centers this item is needed at; an
    # empty list means "all of the Request's preferred centers apply".
    preferred_collection_center_ids: list[UUID] | None = None

    _normalize_unit = field_validator("unit")(_normalize_unit)


class RequestItemResponse(BaseModel):
    """A RequestItem with its live progress summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID
    # Stable, per-Request sequential number (1, 2, ...); drives the display
    # label ("Name #N") and the short item URL.
    item_number: int
    resource_id: UUID
    quantity: int | None
    unit: str | None
    # The item's own subset of the Request's preferred centers (empty = all).
    preferred_collection_center_ids: list[UUID]
    # Distinct ISO/name country values of this item's effective drop-off
    # centers, so a card can show "asking for help from" flags per item.
    countries: list[str]
    description: str | None
    deadline: date | None
    status: RequestStatus
    closed_reason: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
    progress: RequestItemProgress


class RequestItemDetailResponse(RequestItemResponse):
    """A RequestItem enriched with Resource + campaign context for its page.

    Powers the shareable request-item detail page. ``last_activity_at`` is the
    newest of the item's own updates and any comment/commitment activity, so a
    stale item is obvious at a glance.
    """

    resource_name: str
    resource_description: str | None
    resource_image_url: str | None
    resource_source_url: str | None
    request_title: str
    request_status: RequestStatus
    last_activity_at: datetime


class RequestCreate(BaseModel):
    """Create a Request, optionally with items (FR-038).

    Items are optional at creation: a Request may start empty and have
    items added later via ``POST /requests/{id}/items`` (FR-122).
    """

    title: str = Field(min_length=1, max_length=200)
    # "What does the project seek to solve?"
    description: str | None = None
    # "Who is the project for?" (separate prompt on the create form).
    beneficiary: str | None = None
    # How finished items should be packaged for drop-off (grouping, labels, QR).
    packaging_instructions: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    image_focus_x: float = Field(default=50, ge=0, le=100)
    image_focus_y: float = Field(default=50, ge=0, le=100)
    deadline: date | None = None
    preferred_collection_center_ids: list[UUID] = Field(default_factory=list)
    owner_organization_id: UUID | None = None
    items: list[RequestItemCreate] = Field(default_factory=list)

    _normalize_image_url = field_validator("image_url")(_validate_http_url)


class RequestUpdate(BaseModel):
    """Edit campaign-level metadata while the Request is open (FR-042)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    beneficiary: str | None = None
    packaging_instructions: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    image_focus_x: float | None = Field(default=None, ge=0, le=100)
    image_focus_y: float | None = Field(default=None, ge=0, le=100)
    deadline: date | None = None
    preferred_collection_center_ids: list[UUID] | None = None

    _normalize_image_url = field_validator("image_url")(_validate_http_url)


class CloseRequest(BaseModel):
    """Optional reason payload for closing a Request or item (FR-043)."""

    reason: str | None = None


class RequestResponse(BaseModel):
    """Campaign-level Request without its items (list view)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    beneficiary: str | None
    packaging_instructions: str | None
    image_url: str | None
    image_focus_x: float
    image_focus_y: float
    deadline: date | None
    requester_user_id: UUID | None
    requester_organization_id: UUID | None
    created_by_id: UUID
    preferred_collection_center_ids: list[UUID]
    status: RequestStatus
    closed_reason: str | None
    # Publication state (FR-134). Only ``approved`` campaigns reach a viewer
    # who is not a requester or a maintainer, so anything else here means the
    # caller is entitled to see it and the UI should say why it is not live.
    moderation_status: ModerationStatus
    submitted_at: datetime | None
    # The maintainer's note when asking for more information or rejecting.
    # Only ever serialized to someone allowed to see the unpublished campaign.
    review_note: str | None
    reviewed_at: datetime | None
    active: bool
    created_at: datetime
    updated_at: datetime


class RequestListItem(RequestResponse):
    """A campaign for the list view, with a derived help state + last activity.

    ``help_state`` aggregates the items' fulfillment buckets so the directory
    can filter by "needs help / committed / completed"; ``last_activity_at``
    surfaces the newest comment/commitment across the campaign and its items.
    ``countries`` is the distinct set of ISO country codes of the campaign's
    effective drop-off centers, so the directory can flag single-country
    campaigns ("Only Venezuela").
    """

    help_state: HelpState
    last_activity_at: datetime
    countries: list[str]


class RequestDetailResponse(RequestResponse):
    """A Request with its embedded items + per-item progress."""

    items: list[RequestItemResponse]


class RequestReviewNote(BaseModel):
    """A maintainer's note when asking for more information (required)."""

    note: str = Field(min_length=1, max_length=MAX_REVIEW_NOTE_LENGTH)


class RequestRejectNote(BaseModel):
    """A maintainer's reason for rejecting a campaign (optional but urged)."""

    note: str | None = Field(default=None, max_length=MAX_REVIEW_NOTE_LENGTH)
