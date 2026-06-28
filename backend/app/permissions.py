"""Shared authorization helpers.

Phase 1 only needs the global-override check; the polymorphic owner /
member helpers land alongside the organizations and collection-centers
domains in Phase 2.
"""

from app.users.constants import UserRole
from app.users.models import User


def has_global_override(user: User) -> bool:
    """Return True if the user is a maintainer or admin (NFR-006)."""
    return user.role in (UserRole.MAINTAINER, UserRole.ADMIN)
