"""Pydantic request/response models for the users domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.contributions.constants import ContributionStatus
from app.handles import HANDLE_MAX_LENGTH
from app.resources.constants import ResourceCategory

from .constants import Locale, UserRole

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


class ProfileUpdate(BaseModel):
    """Self-edit of the caller's public profile (name, bio, avatar).

    A full replacement of the three editable profile fields: the settings form
    always submits all of them (unchanged values included). Blank strings are
    normalized to ``None`` so clearing a field wipes it rather than storing "".
    Username and email are **not** editable here (username is a one-time pick;
    email changes are not offered in v1).
    """

    full_name: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=BIO_MAX_LENGTH)
    avatar_url: str | None = Field(default=None, max_length=AVATAR_URL_MAX_LENGTH)

    @field_validator("full_name", "bio", "avatar_url")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        """Trim whitespace and treat an empty string as "not set" (``None``)."""
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class PublicProfileResponse(BaseModel):
    """Email-free public view of a user, safe for unauthenticated reads."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None
    avatar_url: str | None
    bio: str | None
    created_at: datetime


class ProfileProjectResponse(BaseModel):
    """One "project the user collaborates on" card (a public contribution).

    Derived from the user's Contributions, each joined to its Request/item,
    Resource, and drop-off Center. Only contributions on **published**
    (``approved``) campaigns are ever surfaced.
    """

    request_id: UUID
    request_title: str
    item_number: int
    resource_id: UUID
    resource_name: str
    resource_image_url: str | None
    resource_category: ResourceCategory
    status: ContributionStatus
    quantity: int
    unit: str | None
    collection_center_name: str | None
    collection_center_country: str | None
    last_activity_at: datetime


class PublicUserProfile(BaseModel):
    """A user's public profile plus the projects they collaborate on."""

    user: PublicProfileResponse
    projects: list[ProfileProjectResponse]
    projects_count: int


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
