"""Pydantic request/response models for the contributions domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.resources.constants import ResourceCategory

from .constants import ContributionStatus


def _normalize_tags(tags: list[str] | None) -> list[str] | None:
    """Normalize maker tags to a unique, trimmed list.

    Trims each tag, drops blanks, and de-duplicates case-insensitively,
    keeping the first-seen casing and order so they stay unique within a
    contribution.
    """
    if tags is None:
        return None
    seen: set[str] = set()
    result: list[str] = []
    for raw in tags:
        tag = raw.strip()
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            result.append(tag)
    return result


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
    tags: list[str]
    active: bool
    created_at: datetime
    updated_at: datetime


class MyContributionResponse(ContributionResponse):
    """A maker's Contribution enriched with its Resource and Request context."""

    request_id: UUID
    request_title: str
    # Per-Request item number, so a maker can tell duplicate parts apart.
    item_number: int
    # The item's chosen unit of measure (e.g. "litros"); null = pieces.
    item_unit: str | None
    resource_id: UUID
    resource_name: str
    resource_image_url: str | None
    # Drives the parts-vs-supply UI: print_3d resources have a "mark printed"
    # step, supplies (any other category) go claimed -> delivered directly.
    resource_category: ResourceCategory
    collection_center_name: str | None
    # The assigned drop-off center's map/location link, if any. Powers the
    # "get directions" button next to the drop-off line.
    collection_center_location_url: str | None
    # The parent Request's preferred drop-off centers (may be empty). When
    # non-empty, the drop-off selector restricts to these; a lone one defaults.
    preferred_collection_center_ids: list[UUID]
    # The maker's item-tracking group token, if they have generated one. Drives
    # the "Tracking" link on each card (null = offer to generate instead).
    tracking_token: str | None


class ItemCommitmentResponse(BaseModel):
    """A public, read-only view of one commitment on a RequestItem.

    Shown on the shareable item page so the community can see who has already
    committed and how far along it is. Deliberately omits the maker's private
    ``notes`` and ``tags``.
    """

    id: UUID
    maker_username: str
    # The maker's picture, carried alongside the username so the commitments
    # list renders the same avatar the comment feed does (same fields as
    # ``activity.schemas.ActorSummary``) without a round trip per row.
    maker_full_name: str | None = None
    maker_avatar_url: str | None = None
    maker_avatar_crop_x: float = 0
    maker_avatar_crop_y: float = 0
    maker_avatar_crop_w: float = 100
    maker_avatar_crop_h: float = 100
    quantity: int
    status: ContributionStatus
    collection_center_name: str | None
    claimed_at: datetime
    prepared_at: datetime | None
    delivered_at: datetime | None
    received_at: datetime | None


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
    """Edit an undelivered Contribution.

    Quantity, notes, and ``collection_center_id`` are editable for the whole
    pre-delivery window — ``claimed`` and ``prepared`` (FR-057) — so a maker
    who finds they can manage more (or fewer) units can resize the commitment
    without releasing it and claiming again. They lock at ``delivered``.
    """

    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = None
    collection_center_id: UUID | None = None
    # Maker's personal labels; editable at any status, unlike quantity/center.
    tags: list[str] | None = None

    _normalize_tags = field_validator("tags")(_normalize_tags)
