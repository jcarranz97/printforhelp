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
    created_at: datetime
    updated_at: datetime


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


class RoleUpdate(BaseModel):
    """Change a user's role (admin only, FR-010)."""

    role: UserRole


class PasswordReset(BaseModel):
    """Admin sets a new password for another account (Phase 1)."""

    new_password: str = Field(min_length=8, max_length=128)
