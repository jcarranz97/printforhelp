"""Auth business logic: password policy, JWT, authentication."""

import hashlib
import logging
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.users.models import User

from .constants import MIN_PASSWORD_LENGTH
from .email import send_password_reset_email
from .exceptions import (
    InactiveUserExceptionError,
    IncorrectPasswordExceptionError,
    InvalidCredentialsExceptionError,
    InvalidResetTokenExceptionError,
    InvalidTokenExceptionError,
    WeakPasswordExceptionError,
)
from .models import PasswordResetToken
from .utils import hash_password, verify_password

logger = logging.getLogger(__name__)


def validate_password_strength(password: str) -> None:
    """Enforce the password policy (FR-002): >= 8 chars, a letter, a digit."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordExceptionError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    if not any(c.isalpha() for c in password):
        raise WeakPasswordExceptionError("Password must contain at least one letter.")
    if not any(c.isdigit() for c in password):
        raise WeakPasswordExceptionError("Password must contain at least one digit.")


def authenticate(db: Session, identifier: str, password: str) -> User:
    """Return the user for valid credentials, else raise (FR-003).

    ``identifier`` may be either an email (used by self-registered
    accounts) or a username (admin-provisioned and system accounts).
    Both are matched case-insensitively; lookup falls back to username.
    """
    normalized = identifier.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == normalized).first()
    if user is None:
        user = db.query(User).filter(func.lower(User.username) == normalized).first()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsExceptionError
    if not user.active:
        raise InactiveUserExceptionError
    return user


def create_access_token(user_id: UUID) -> str:
    """Issue a signed JWT for the given user id."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> UUID:
    """Return the user id encoded in the token, or raise on failure."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject = payload.get("sub")
        if subject is None:
            raise InvalidTokenExceptionError
        return UUID(subject)
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidTokenExceptionError from exc


def change_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    """Change a user's password after verifying the current one (FR-005)."""
    if not verify_password(current_password, user.password_hash):
        raise IncorrectPasswordExceptionError
    validate_password_strength(new_password)
    user.password_hash = hash_password(new_password)
    db.commit()


def _hash_reset_token(raw_token: str) -> str:
    """Hash a raw reset token for storage/lookup (SHA-256 hex)."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def request_password_reset(db: Session, email: str) -> None:
    """Start the forgot-password flow for an email address.

    Always succeeds silently: if an active account with that email exists,
    we create a one-time token and email a reset link; otherwise we do
    nothing. The endpoint returns the same response either way so an
    attacker cannot tell which emails are registered.
    """
    normalized = email.strip().lower()
    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized, User.active.is_(True))
        .first()
    )
    if user is None:
        return

    # Retire any older pending tokens so only the newest link works.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.active.is_(True),
    ).update({PasswordResetToken.active: False})

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=expires_at,
        )
    )
    db.commit()

    reset_url = f"{settings.PUBLIC_APP_BASE_URL}/reset-password?token={raw_token}"
    try:
        send_password_reset_email(user.email, reset_url)  # type: ignore[arg-type]
    except (OSError, smtplib.SMTPException):
        # A mail-server hiccup must not fail the request (or reveal which
        # emails exist). The token is already stored; the user can retry.
        logger.exception("Failed to send password reset email to %s", user.email)


def reset_password_with_token(db: Session, raw_token: str, new_password: str) -> None:
    """Redeem a reset token and set the new password.

    Raises ``InvalidResetTokenExceptionError`` if the token is unknown,
    already used, expired, or belongs to a deactivated account.
    """
    token_hash = _hash_reset_token(raw_token)
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.active.is_(True),
        )
        .first()
    )
    if record is None or record.expires_at <= datetime.now(UTC):
        raise InvalidResetTokenExceptionError

    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None or not user.active:
        raise InvalidResetTokenExceptionError

    validate_password_strength(new_password)
    user.password_hash = hash_password(new_password)
    record.used_at = datetime.now(UTC)
    record.active = False
    db.commit()
