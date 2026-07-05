"""Enums and constants for the item-tracking domain."""

from enum import StrEnum
from string import ascii_uppercase

# A public tracking code doubles as the access secret: anyone holding one can
# read the timeline *and* append to it (see ``service._can_view``), so codes
# must stay UNGUESSABLE — never a sequential index, which would let anyone
# enumerate every timeline and post to it without holding the physical QR.
#
# We use a short uppercase base32 code (RFC 4648 alphabet, no look-alike
# 0/1/8/9) instead of the old 22-char ``token_urlsafe`` slug: 8 symbols over a
# 32-char alphabet is 40 bits of entropy, still unguessable, but short enough
# that the encoded ``{base}/t/{code}`` URL stays at a low QR version —
# noticeably easier to scan off a small or curved 3D print (the exact version
# also depends on the deploy domain's length). Uppercase-only also lets the QR
# use its compact alphanumeric mode.
# Generation retries on the (rare) collision across the group + item spaces.
TRACKING_TOKEN_ALPHABET = ascii_uppercase + "234567"
TRACKING_TOKEN_LENGTH = 8
TRACKING_TOKEN_COLLISION_RETRIES = 8

# Guard rails so a single Contribution cannot spawn an unbounded number of
# per-unit tracking items (and QR codes) in one request.
MAX_TRACKED_UNITS = 500

MAX_RECORD_DESCRIPTION_LENGTH = 10_000
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Cap the maker note printed on each label so it always fits a sticker.
MAX_CONTRIBUTOR_MESSAGE_LENGTH = 100

# Rendered on the label bundle when the maker includes a message but has not
# written a custom one. Spanish to match the v1 UI; no emoji (the print font
# has no emoji glyphs, though it does render accents).
DEFAULT_CONTRIBUTOR_MESSAGE = (
    "Esta pieza fue impresa con cariño por la comunidad de makers de "
    "PrintForHelp para ayudar a quienes más lo necesitan. ¡Gracias por "
    "confiar en nosotros!"
)


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
    MESSAGE_NOT_FOUND = "MESSAGE_NOT_FOUND"
