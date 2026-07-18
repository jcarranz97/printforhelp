"""SQLAlchemy model for user accounts."""

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import Locale, UserRole


class User(BaseModel):
    """A primary user account (FR-007 / FR-009)."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    # Nullable: accounts that predate self-registration (admin, anonymous,
    # admin-provisioned users) have no email. Self-registered users always
    # set both ``email`` and ``full_name``.
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Public profile picture (a stored upload URL from ``POST /uploads/images``),
    # rendered as a circular avatar everywhere the user appears. Nullable: a
    # user without one falls back to their initials.
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Short, self-authored public blurb shown on the profile page (FR — public
    # profiles). Nullable/optional; capped so it stays a one-liner.
    bio: Mapped[str | None] = mapped_column(String(280), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Google account subject ("sub") for users who sign in with Google.
    # Nullable: password-only and system accounts never set it.
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    # False only for Google accounts that still carry the auto-generated
    # username and must pick their own before using the app. Everyone else
    # (email sign-ups, admin-provisioned, system) chose/was given one.
    username_chosen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=UserRole.USER,
    )
    preferred_locale: Mapped[Locale] = mapped_column(
        Enum(
            Locale,
            name="locale_code",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=Locale.ES,
    )


class UserFlag(BaseModel):
    """A generic yes/no attribute attached to a user.

    Keys come from ``app/users/flags.py`` (``FLAG_REGISTRY``). One row per
    ``(user_id, key)`` (upserted). ``value`` is the answer/grant; the *absence*
    of a row means "unknown" (tri-state). ``source`` + ``set_by_id`` record
    provenance for auditability. See the registry for the trust model (traits
    are self-declared; capabilities are admin-granted).
    """

    __tablename__ = "user_flags"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_flag_key"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    set_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
