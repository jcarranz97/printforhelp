"""Pydantic request/response models for the users domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.handles import HANDLE_MAX_LENGTH

from .constants import Locale, UserRole


class UserResponse(BaseModel):
    """Public representation of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    full_name: str | None
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
