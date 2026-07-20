"""Pydantic request/response models for the users domain."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.handles import HANDLE_MAX_LENGTH

from .constants import Locale, ProfileActivityKind, UserRole

BIO_MAX_LENGTH = 280
AVATAR_URL_MAX_LENGTH = 500


class UserResponse(BaseModel):
    """Representation of a user account for the account owner / admins.

    Includes ``email`` and so must never back a public, unauthenticated read —
    use :class:`PublicProfileResponse` for that.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    full_name: str | None
    avatar_url: str | None
    avatar_crop_x: float
    avatar_crop_y: float
    avatar_crop_w: float
    avatar_crop_h: float
    bio: str | None
    role: UserRole
    preferred_locale: Locale
    active: bool
    # False while a Google user still needs to pick their own username.
    username_chosen: bool
    created_at: datetime
    updated_at: datetime


class MeResponse(UserResponse):
    """The authenticated user's own profile, plus their generic flags.

    ``flags`` holds only answered/granted flags (``{key: bool}``); an absent
    key means "unknown" (e.g. the maker prompt has not been answered).
    """

    flags: dict[str, bool]
    # When the user may next rename their handle; null means "right now". Lets
    # the settings form lock the field without guessing the rule. Deliberately
    # required rather than defaulted: `MeResponse` is built in more than one
    # place, and a default would let a caller silently report "no cooldown".
    username_change_available_at: datetime | None


def _blank_to_none(value: str | None) -> str | None:
    """Trim whitespace and treat an empty string as "not set" (``None``)."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class ProfileUpdate(BaseModel):
    """Self-edit of the caller's name and bio.

    A full replacement of both fields: the settings form always submits them
    together (unchanged values included). Blank strings are normalized to
    ``None`` so clearing a field wipes it rather than storing "".

    The **avatar is deliberately not here** — it has its own endpoint. The UI
    applies a new picture the moment it is cropped, while name/bio are saved by
    the form's button, so folding them together would make each save clobber
    the other's unsaved state. Username and email are not editable at all
    (username is a one-time pick; email changes are not offered in v1).
    """

    full_name: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=BIO_MAX_LENGTH)

    _normalize = field_validator("full_name", "bio")(_blank_to_none)


class AvatarUpdate(BaseModel):
    """Set or clear the caller's profile picture and the crop shown in it.

    ``avatar_url`` of ``None`` removes the picture. The crop is the square
    region shown in the circle, in percent of the source image: where it sits
    (x/y) and how much of it is used (w/h) — the size is what makes zooming
    possible. It defaults to the whole image, which renders as a centred cover
    fit.
    """

    avatar_url: str | None = Field(default=None, max_length=AVATAR_URL_MAX_LENGTH)
    avatar_crop_x: float = Field(default=0, ge=0, le=100)
    avatar_crop_y: float = Field(default=0, ge=0, le=100)
    avatar_crop_w: float = Field(default=100, gt=0, le=100)
    avatar_crop_h: float = Field(default=100, gt=0, le=100)

    _normalize = field_validator("avatar_url")(_blank_to_none)


class PublicProfileResponse(BaseModel):
    """Email-free public view of a user, safe for unauthenticated reads."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None
    avatar_url: str | None
    avatar_crop_x: float
    avatar_crop_y: float
    avatar_crop_w: float
    avatar_crop_h: float
    bio: str | None
    created_at: datetime


class ProfileActivityItem(BaseModel):
    """One project line inside a timeline entry (the bars in the breakdown)."""

    request_id: UUID
    request_title: str
    item_number: int
    resource_name: str
    quantity: int
    unit: str | None


class ProfileActivityEntry(BaseModel):
    """One grouped action on the contribution timeline.

    Contributions of the same ``kind`` within a month are rolled up into a
    single entry — "Printed 468 pieces across 5 projects" — rather than listed
    individually, which is what makes the timeline readable.

    Entries are a history, so the same commitment legitimately appears under
    several stages as it progresses; use the month's ``contributions_count``
    for a deduplicated total.
    """

    kind: ProfileActivityKind
    # The most recent event in the group; the UI shows it as the entry's date.
    occurred_at: datetime
    total_quantity: int
    request_count: int
    # The per-project breakdown rendered as labelled bars, largest first.
    items: list[ProfileActivityItem]
    # Set when the whole group belongs to one campaign, so the summary can name
    # it ("Claimed 44 pieces in Silbatos por la Vida") instead of counting.
    single_request_title: str | None
    # The unit shared by every contribution in the group (null = countable
    # pieces). Null when they disagree, in which case the UI falls back to the
    # generic wording; the per-project lines always carry their own unit.
    unit: str | None
    # Only for ``renamed`` entries: the handles before and after the change.
    # A rename is a profile event, not a contribution — it appears on the
    # timeline but never counts toward the totals or the calendar.
    renamed_from: str | None = None
    renamed_to: str | None = None
    # Only for ``renamed`` entries, and only populated for maintainer/admin
    # viewers: the change's id (so it can be targeted for hiding) and whether it
    # is currently hidden. Regular viewers never see hidden renames, so these
    # stay null for them.
    rename_id: UUID | None = None
    rename_hidden: bool = False


class ProfileActivityMonth(BaseModel):
    """A month of timeline entries, newest month first."""

    year: int
    month: int = Field(ge=1, le=12)
    # Distinct commitments this month touched. The stage entries below overlap
    # (one commitment claimed *and* printed in the month appears in both), so
    # this is deduplicated to answer "how much did they contribute this month?"
    contributions_count: int
    entries: list[ProfileActivityEntry]


class ProfileContributionDay(BaseModel):
    """One day of the contribution calendar (the heat-map squares).

    ``count`` is the number of distinct commitments active that day, so a
    commitment claimed on Monday and printed on Wednesday lights both.
    """

    date: date
    count: int


class ProfileActivityPage(BaseModel):
    """One page of the timeline: a few months plus a cursor for the next.

    Paged by months that *have* activity rather than calendar months, so
    "Show more activity" always reveals something instead of walking through
    empty gaps. The cursor is a timestamp rather than an offset: it cannot
    split a month across pages and stays correct if new activity lands while
    the reader is paging.
    """

    months: list[ProfileActivityMonth]
    # Pass back as ``before`` to fetch the next (older) page; null when done.
    next_before: datetime | None
    has_more: bool


class UsernameChangeVisibility(BaseModel):
    """Maintainer/admin toggle for a rename's visibility on the timeline."""

    hidden: bool


class UsernameChangeResponse(BaseModel):
    """The rename after a visibility toggle: its id and current hidden state."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hidden: bool


class PublicUserProfile(BaseModel):
    """A user's public profile plus the first page of their timeline."""

    user: PublicProfileResponse
    # The calendar year being shown, or null for the default "last 12 months".
    selected_year: int | None
    # Years the user has activity in, newest first — drives the year selector.
    available_years: list[int]
    # Distinct commitments in the selected window (the headline count).
    contributions_total: int
    # Per-day counts for the same window, driving the calendar heat map. Only
    # days with activity are listed; the UI fills in the empty squares.
    contribution_days: list[ProfileContributionDay]
    activity: ProfileActivityPage


class UserFlagsResponse(BaseModel):
    """A user's current flag map, returned after a set/grant."""

    flags: dict[str, bool]


class FlagUpdate(BaseModel):
    """Set a flag's yes/no value."""

    value: bool


class UserSearchResult(BaseModel):
    """Lightweight user record for the @mention typeahead."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None


class UserCreate(BaseModel):
    """Admin-provisioned account creation payload (FR-007 / Phase 1)."""

    username: str = Field(min_length=1, max_length=HANDLE_MAX_LENGTH)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER
    preferred_locale: Locale = Locale.ES


class UserRegister(BaseModel):
    """Self-registration payload: name + username + email + password (FR-001)."""

    full_name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=HANDLE_MAX_LENGTH)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UsernameChoice(BaseModel):
    """A user picking their own username (Google onboarding).

    Length only at the schema layer; the full URL-safe handle rules
    (character set, edges, reserved words, cross-namespace uniqueness) are
    enforced in the service via ``app.handles`` so the error code is precise.
    """

    username: str = Field(min_length=1, max_length=HANDLE_MAX_LENGTH)


class LocaleChoice(BaseModel):
    """A user setting their own preferred locale (drives UI + email language)."""

    locale: Locale


class RoleUpdate(BaseModel):
    """Change a user's role (admin only, FR-010)."""

    role: UserRole


class PasswordReset(BaseModel):
    """Admin sets a new password for another account (Phase 1)."""

    new_password: str = Field(min_length=8, max_length=128)
