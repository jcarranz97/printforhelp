"""Common dependency-injection types reused across domains."""

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import get_current_active_user, get_current_user
from app.database import get_db
from app.permissions import has_global_override
from app.users.constants import UserRole
from app.users.exceptions import RoleRequiredExceptionError
from app.users.models import User

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]


def require_admin(current_user: CurrentActiveUser) -> User:
    """Require the caller to be an admin (FR-010 / FR-012)."""
    if current_user.role != UserRole.ADMIN:
        raise RoleRequiredExceptionError("admin")
    return current_user


def require_maintainer(current_user: CurrentActiveUser) -> User:
    """Require the caller to be a maintainer or admin (NFR-006)."""
    if not has_global_override(current_user):
        raise RoleRequiredExceptionError("maintainer")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
MaintainerUser = Annotated[User, Depends(require_maintainer)]

__all__ = [
    "AdminUser",
    "CurrentActiveUser",
    "CurrentUser",
    "MaintainerUser",
    "get_db",
]
