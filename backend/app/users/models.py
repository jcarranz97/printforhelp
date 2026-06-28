"""SQLAlchemy model for user accounts."""

from sqlalchemy import Enum, String
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
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
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
