"""SQLAlchemy models for the auth domain."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel


class PasswordResetToken(BaseModel):
    """A one-time token that lets a user set a new password.

    We never store the raw token — only its SHA-256 hash — so a leaked
    database dump cannot be used to reset anyone's password. A row is
    ``used_at``-stamped once redeemed and expires after
    ``PASSWORD_RESET_TOKEN_EXPIRE_MINUTES``.
    """

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
