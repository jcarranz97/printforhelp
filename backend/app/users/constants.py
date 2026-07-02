"""Enums and error codes for the users domain."""

from enum import StrEnum


class UserRole(StrEnum):
    """Application-wide user roles (FR-009)."""

    USER = "user"
    MAINTAINER = "maintainer"
    ADMIN = "admin"


# Username of the system account that owns anonymously-submitted assets
# (e.g. collection centers registered without logging in). It has an
# unguessable password and is never meant to authenticate.
ANONYMOUS_USERNAME = "anonymous"

# Defaults for the @mention typeahead search (GET /users/search).
USER_SEARCH_LIMIT_DEFAULT = 8
USER_SEARCH_LIMIT_MAX = 25


class Locale(StrEnum):
    """UI locales a user can prefer (FR-006 / NFR-015)."""

    ES = "es"
    EN = "en"


class ErrorCode(StrEnum):
    """Error codes raised by the users domain."""

    USER_NOT_FOUND = "USER_NOT_FOUND"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    ROLE_REQUIRED = "ROLE_REQUIRED"
    LOCKOUT_PROTECTION = "LOCKOUT_PROTECTION"
    UNKNOWN_FLAG = "UNKNOWN_FLAG"
    FLAG_NOT_SELF_ASSIGNABLE = "FLAG_NOT_SELF_ASSIGNABLE"
