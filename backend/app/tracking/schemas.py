"""Pydantic request/response models for the item-tracking domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import (
    MAX_CONTRIBUTOR_MESSAGE_LENGTH,
    MAX_RECORD_DESCRIPTION_LENGTH,
    TrackingTargetKind,
    TrackingVisibility,
)


def _normalize_tags(tags: list[str] | None) -> list[str] | None:
    """Trim, drop blanks, and de-duplicate tags case-insensitively.

    Mirrors the contributions-domain normalizer so record tags behave like
    every other tag input in the product.
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


class TrackingItemResponse(BaseModel):
    """One printed unit's tracking handle."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tracking_token: str
    sequence: int


class TrackingRecordAuthor(BaseModel):
    """Public author summary; ``None`` username means an anonymous post."""

    id: UUID | None
    username: str | None


class TrackingRecordResponse(BaseModel):
    """A single timeline entry."""

    id: UUID
    target_kind: TrackingTargetKind
    target_token: str
    # For item records, which unit (1-based) of the group this belongs to.
    item_sequence: int | None
    author: TrackingRecordAuthor
    description: str
    tags: list[str]
    created_at: datetime
    # Whether the caller may edit this record's tags (author/owner/admin). The
    # frontend uses it to decide when to render the inline tag editor.
    can_edit_tags: bool = False


class PublicTrackingResponse(BaseModel):
    """Public ``/track/{token}`` payload: item summary plus its timeline."""

    target_kind: TrackingTargetKind
    tracking_token: str
    # The owning group's id, so a logged-in viewer can watch/unwatch the
    # tracking timeline via the generic ``/watches`` endpoints.
    group_id: UUID
    visibility: TrackingVisibility
    resource_name: str
    resource_image_url: str | None
    contribution_status: str
    quantity: int
    # Present only for an item token: which unit of the group this is.
    item_sequence: int | None
    records: list[TrackingRecordResponse]
    # Whether the caller may append records / edit tags on this timeline.
    can_contribute: bool
    # Whether the current (logged-in) viewer is watching this group; always
    # False for guests, who cannot receive notifications.
    watching: bool = False


class TrackingGroupMemberSummary(BaseModel):
    """A named group-visibility member."""

    id: UUID
    username: str


class OwnerTrackingResponse(BaseModel):
    """Owner-facing view: the whole group, all items, and settings."""

    group_id: UUID
    contribution_id: UUID
    tracking_token: str
    visibility: TrackingVisibility
    quantity: int
    resource_name: str
    resource_image_url: str | None
    # The Resource's optional print label; when present the manage page offers
    # an "include label" checkbox for the QR bundle downloads.
    resource_label_image_url: str | None
    members: list[TrackingGroupMemberSummary]
    items: list[TrackingItemResponse]
    # Group-level records plus every item's records, newest first.
    records: list[TrackingRecordResponse]
    # Whether the owner is watching this group (they auto-watch on generate,
    # but may unwatch); powers the watch toggle on the manage page.
    watching: bool = False


class TrackingUpdate(BaseModel):
    """Set visibility and the named group-visibility members."""

    visibility: TrackingVisibility
    # Usernames granted access under the ``group`` tier; unknown names are
    # ignored. Ignored entirely for ``private`` / ``public``.
    member_usernames: list[str] = Field(default_factory=list)


class ContributorMessageCreate(BaseModel):
    """Save a reusable contributor-message template for the current user."""

    body: str = Field(min_length=1, max_length=MAX_CONTRIBUTOR_MESSAGE_LENGTH)


class ContributorMessageResponse(BaseModel):
    """One of the user's saved contributor-message templates."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    body: str
    created_at: datetime


class RecordCreate(BaseModel):
    """Append a record after scanning a QR (open per visibility)."""

    description: str = Field(min_length=1, max_length=MAX_RECORD_DESCRIPTION_LENGTH)
    tags: list[str] = Field(default_factory=list)
    # A logged-in author may post without attaching their name. Ignored for
    # guests (they are always anonymous).
    display_anonymous: bool = False

    _normalize_tags = field_validator("tags")(_normalize_tags)


class RecordTagsUpdate(BaseModel):
    """Edit a record's tags (author / contribution owner / maintainer)."""

    tags: list[str]

    _normalize_tags = field_validator("tags")(_normalize_tags)
