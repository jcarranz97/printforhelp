"""Auth business logic: password policy, JWT, authentication."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.users.models import User

from .constants import MIN_PASSWORD_LENGTH
from .exceptions import (
    InactiveUserExceptionError,
    IncorrectPasswordExceptionError,
    InvalidCredentialsExceptionError,
    InvalidTokenExceptionError,
    WeakPasswordExceptionError,
)
from .utils import hash_password, verify_password


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


def authenticate(db: Session, username: str, password: str) -> User:
    """Return the user for valid credentials, else raise (FR-003)."""
    user = db.query(User).filter(User.username == username).first()
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
