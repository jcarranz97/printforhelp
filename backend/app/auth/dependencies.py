"""FastAPI dependencies that resolve the current user from a JWT."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.users.models import User

from . import service
from .exceptions import InactiveUserExceptionError, InvalidTokenExceptionError

# auto_error=False so missing tokens flow through our envelope, not
# FastAPI's default 401 body.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    """Resolve the bearer token to a user (raises 401 on failure)."""
    if not token:
        raise InvalidTokenExceptionError
    user_id = service.decode_access_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise InvalidTokenExceptionError
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require the resolved user to be active (FR-013)."""
    if not current_user.active:
        raise InactiveUserExceptionError
    return current_user
