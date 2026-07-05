"""Shared rules for public handles (usernames + organization handles).

A **handle** is the URL-safe public identifier that appears in a profile
URL — ``/{handle}``. A user's ``username`` and an organization's ``handle``
draw from the **same namespace**, so a handle must be:

* **URL-safe** — letters, numbers, and single ``.`` ``_`` ``-`` separators,
  never at the start/end and never repeated (this also blocks the
  path-traversal segments ``.`` and ``..``);
* **3-50 characters**;
* **unique across both users and organizations** (case-insensitive), so
  ``/{username}`` and ``/{orgname}`` can never collide; and
* **not a reserved word** that would shadow an application route
  (``/login``, ``/parts``, ``/admin``, …).

The format/length/reserved rules live here as the single source of truth;
service layers add the cross-namespace uniqueness check via
:func:`is_handle_taken`. Organization handles are derived from the org's
display name with :func:`slugify_handle`.
"""

import re
import unicodedata
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exceptions import AppExceptionError
from app.organizations.models import Organization
from app.users.models import User

HANDLE_MIN_LENGTH = 3
HANDLE_MAX_LENGTH = 50

# Start and end alphanumeric; a single ``.`` ``_`` or ``-`` may separate
# alphanumeric runs but never repeats or sits at an edge. Length is checked
# separately so the error messages can be specific.
HANDLE_REGEX = re.compile(r"^[A-Za-z0-9]+([._-][A-Za-z0-9]+)*$")

# Handles that would shadow an application route or a system concept. Kept
# lowercase; the check is case-insensitive. Deliberately excludes short,
# legitimate words like "org" so real names are not blocked.
RESERVED_HANDLES = frozenset(
    {
        # System / auth
        "anonymous",
        "admin",
        "administrator",
        "root",
        "system",
        "support",
        "help",
        "api",
        "auth",
        "login",
        "logout",
        "signin",
        "signout",
        "register",
        "signup",
        "me",
        "self",
        "account",
        "accounts",
        "settings",
        "profile",
        "profiles",
        "user",
        "users",
        # NB: bare "org" is intentionally NOT reserved — it is a legitimate
        # short display name. Only the plural/route forms are reserved.
        "orgs",
        "organization",
        "organizations",
        # Current application routes (frontend app/ segments)
        "about",
        "centers",
        "center",
        "parts",
        "part",
        "requests",
        "request",
        "supplies",
        "supply",
        "track",
        "tracking",
        "tracking-bundle",
        "my-contributions",
        "contributions",
        "contribution",
        "forgot-password",
        "reset-password",
        "notifications",
        "search",
        "new",
        "edit",
        # Static / infra
        "docs",
        "static",
        "public",
        "assets",
        "favicon",
        "robots",
        "sitemap",
        "terms",
        "privacy",
        "null",
        "undefined",
        "true",
        "false",
    }
)


class InvalidHandleError(AppExceptionError):
    """Raised when a handle fails the format/length rules (422)."""

    def __init__(self, message: str, error_code: str = "INVALID_USERNAME") -> None:
        super().__init__(error_code=error_code, message=message, status_code=422)


class HandleReservedError(AppExceptionError):
    """Raised when a handle matches a reserved word (409)."""

    def __init__(self, handle: str, error_code: str = "USERNAME_RESERVED") -> None:
        super().__init__(
            error_code=error_code,
            message=f"'{handle}' is reserved and cannot be used.",
            status_code=409,
        )


def validate_handle(value: str, *, error_code: str = "INVALID_USERNAME") -> str:
    """Validate a handle's format/length/reserved rules and return it trimmed.

    Does **not** check cross-namespace uniqueness (that needs a DB session;
    use :func:`is_handle_taken`). ``error_code`` lets callers surface a
    domain-specific code (e.g. ``INVALID_USERNAME`` vs ``INVALID_ORG_HANDLE``).
    """
    handle = value.strip()
    reserved_code = (
        "ORG_HANDLE_RESERVED"
        if error_code == "INVALID_ORG_HANDLE"
        else "USERNAME_RESERVED"
    )
    if not (HANDLE_MIN_LENGTH <= len(handle) <= HANDLE_MAX_LENGTH):
        raise InvalidHandleError(
            f"Must be {HANDLE_MIN_LENGTH}-{HANDLE_MAX_LENGTH} characters.",
            error_code,
        )
    if not HANDLE_REGEX.match(handle):
        raise InvalidHandleError(
            "May use letters, numbers, and . _ - only (not at the start or "
            "end, and never repeated).",
            error_code,
        )
    if handle.lower() in RESERVED_HANDLES:
        raise HandleReservedError(handle, reserved_code)
    return handle


def is_handle_taken(
    db: Session,
    value: str,
    *,
    exclude_user_id: UUID | None = None,
    exclude_org_id: UUID | None = None,
) -> bool:
    """Return True if ``value`` is used by any user or organization.

    Case-insensitive and cross-namespace: a username and an org handle share
    one namespace so ``/{username}`` and ``/{orghandle}`` can never collide.
    Soft-deleted rows still count — a freed handle is not reused, so old
    profile URLs never silently point at a different account.
    """
    needle = value.strip().lower()

    user_q = db.query(User.id).filter(func.lower(User.username) == needle)
    if exclude_user_id is not None:
        user_q = user_q.filter(User.id != exclude_user_id)
    if user_q.first() is not None:
        return True

    org_q = db.query(Organization.id).filter(func.lower(Organization.handle) == needle)
    if exclude_org_id is not None:
        org_q = org_q.filter(Organization.id != exclude_org_id)
    return org_q.first() is not None


def slugify_handle(name: str) -> str:
    """Derive a URL-safe base handle from a free-text display name.

    Lowercases, strips accents, and collapses every run of non-alphanumeric
    characters into a single hyphen. Guarantees a non-empty result that is at
    least :data:`HANDLE_MIN_LENGTH` long; the caller still resolves collisions
    (see :func:`unique_org_handle`).
    """
    ascii_name = (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not slug:
        slug = "org"
    if len(slug) < HANDLE_MIN_LENGTH:
        slug = f"{slug}-org"
    return slug[:HANDLE_MAX_LENGTH].strip("-")


def unique_org_handle(
    db: Session, name: str, *, exclude_org_id: UUID | None = None
) -> str:
    """Return a unique, valid org handle derived from ``name``.

    Appends ``-2``, ``-3``, … until the handle is free across the shared
    namespace and not reserved. Used for backfilling legacy organizations
    where rejecting a duplicate is not an option; new creates instead reject
    a collision so the likely duplicate surfaces to the user.
    """
    base = slugify_handle(name)
    candidate = base
    suffix = 1
    while candidate.lower() in RESERVED_HANDLES or is_handle_taken(
        db, candidate, exclude_org_id=exclude_org_id
    ):
        suffix += 1
        candidate = f"{base}-{suffix}"[:HANDLE_MAX_LENGTH].strip("-")
    return candidate
