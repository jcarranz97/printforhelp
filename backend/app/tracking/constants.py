"""Enums and constants for the item-tracking domain."""

from enum import StrEnum

# Bytes of entropy for ``secrets.token_urlsafe`` — 16 yields a 22-char slug,
# unguessable enough to double as the public access secret (GDT-style).
TRACKING_TOKEN_BYTES = 16

# Guard rails so a single Contribution cannot spawn an unbounded number of
# per-unit tracking items (and QR codes) in one request.
MAX_TRACKED_UNITS = 500

MAX_RECORD_DESCRIPTION_LENGTH = 10_000
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class TrackingVisibility(StrEnum):
    """Who may read (and therefore append to) a tracking timeline.

    - ``private``: only the contribution owner and maintainers/admins.
    - ``group``: the above plus the named ``TrackingGroupMember`` users.
    - ``public``: anyone holding the token (the QR link is the access key).
    """

    PRIVATE = "private"
    GROUP = "group"
    PUBLIC = "public"


class TrackingTargetKind(StrEnum):
    """Which token was resolved — a whole group or a single item."""

    GROUP = "group"
    ITEM = "item"


class ErrorCode(StrEnum):
    """Error codes raised by the tracking domain."""

    TRACKING_NOT_FOUND = "TRACKING_NOT_FOUND"
    TRACKING_ALREADY_EXISTS = "TRACKING_ALREADY_EXISTS"
    TRACKING_FORBIDDEN = "TRACKING_FORBIDDEN"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    RECORD_EDIT_FORBIDDEN = "RECORD_EDIT_FORBIDDEN"
