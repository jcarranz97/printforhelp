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
    INVALID_USERNAME = "INVALID_USERNAME"
    USERNAME_RESERVED = "USERNAME_RESERVED"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    ROLE_REQUIRED = "ROLE_REQUIRED"
    LOCKOUT_PROTECTION = "LOCKOUT_PROTECTION"
    UNKNOWN_FLAG = "UNKNOWN_FLAG"
    USERNAME_CHANGE_TOO_SOON = "USERNAME_CHANGE_TOO_SOON"
    FLAG_NOT_SELF_ASSIGNABLE = "FLAG_NOT_SELF_ASSIGNABLE"
    USERNAME_ALREADY_SET = "USERNAME_ALREADY_SET"


class ProfileActivityKind(StrEnum):
    """The maker actions shown on a public profile's contribution timeline.

    Each maps to one Contribution lifecycle timestamp: ``claimed_at``,
    ``prepared_at`` and ``delivered_at``. ``received``/``released`` are
    deliberately absent — receiving is the center's action, not the maker's,
    and a released commitment is a withdrawal rather than a contribution.
    """

    CLAIMED = "claimed"
    PREPARED = "prepared"
    DELIVERED = "delivered"
    # Not a contribution: a profile event (renaming the public handle). It
    # appears on the timeline but never counts toward the contribution totals.
    RENAMED = "renamed"


# The "contributions in the last year" headline covers a rolling 12 months,
# matching the GitHub-style profile it is modelled on. The timeline itself is
# not limited to this window — it pages back through the full history.
PROFILE_ACTIVITY_DAYS = 365

# How many months the timeline returns per page. Counted in months that
# actually *have* activity, not calendar months, so "Show more activity" always
# reveals something instead of scrolling through empty gaps.
PROFILE_ACTIVITY_MONTHS_PAGE = 2
PROFILE_ACTIVITY_MONTHS_MAX = 12


# How long a user must wait between renaming their handle. A rename breaks
# every existing link to their profile, so it is deliberately not something to
# do casually; the limit is enforced from the ``username_changes`` history.
USERNAME_CHANGE_COOLDOWN_DAYS = 7
