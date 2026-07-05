"""Pydantic request/response models for the users domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER
    preferred_locale: Locale = Locale.ES


class UserRegister(BaseModel):
    """Self-registration payload: name + username + email + password (FR-001)."""

    full_name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UsernameChoice(BaseModel):
    """A user picking their own username (Google onboarding).

    3-32 chars, letters/numbers and ``. _ -`` only.
    """

    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")


class RoleUpdate(BaseModel):
    """Change a user's role (admin only, FR-010)."""

    role: UserRole


class PasswordReset(BaseModel):
    """Admin sets a new password for another account (Phase 1)."""

    new_password: str = Field(min_length=8, max_length=128)
