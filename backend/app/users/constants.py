"""Enums and error codes for the users domain."""

from enum import StrEnum


class UserRole(StrEnum):
    """Application-wide user roles (FR-009)."""

    USER = "user"
    MAINTAINER = "maintainer"
    ADMIN = "admin"


class Locale(StrEnum):
    """UI locales a user can prefer (FR-006 / NFR-015)."""

    ES = "es"
    EN = "en"


class ErrorCode(StrEnum):
    """Error codes raised by the users domain."""

    USER_NOT_FOUND = "USER_NOT_FOUND"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    ROLE_REQUIRED = "ROLE_REQUIRED"
    LOCKOUT_PROTECTION = "LOCKOUT_PROTECTION"
