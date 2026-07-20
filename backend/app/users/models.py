"""SQLAlchemy model for user accounts."""

import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, String, UniqueConstraint, text
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
    # The square region of ``avatar_url`` shown in the circular avatar, as
    # percentages of the source image: position (x/y) and size (w/h). This is a
    # crop *rectangle* rather than a focal point so the user can both pan and
    # **zoom** — picking a small circle out of a large picture. Percentages keep
    # it container-independent: the same numbers render the identical crop at
    # every avatar size. 0/0/100/100 means "no crop chosen" and renders as a
    # centred cover fit.
    avatar_crop_x: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    avatar_crop_y: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    avatar_crop_w: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="100"
    )
    avatar_crop_h: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="100"
    )
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


class UsernameChange(BaseModel):
    """An append-only record of a user renaming their public handle.

    Two jobs: it surfaces the rename on the profile timeline ("changed username
    from A to B"), and it is the source of truth for the rename cooldown — the
    limit is derived from this history rather than a mutable column on the
    user, so it cannot drift out of sync with what actually happened.

    ``from_username``/``to_username`` are plain strings, not FKs: they are a
    snapshot of the handles at that moment, and must survive further renames.
    """

    __tablename__ = "username_changes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # Matches ``users.username`` (the shared handle length lives in
    # ``app.handles``, which cannot be imported here without a cycle).
    from_username: Mapped[str] = mapped_column(String(64), nullable=False)
    to_username: Mapped[str] = mapped_column(String(64), nullable=False)
    # A maintainer/admin can hide a rename from the public timeline — e.g. one
    # that reveals an old email-as-handle. Hidden rows stay in the history (so
    # the cooldown, which reads ``active``, is untouched) but are shown only to
    # maintainers/admins. Kept separate from ``active`` on purpose: ``active``
    # is the rename-cooldown source of truth, so soft-deleting would corrupt it.
    hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
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
