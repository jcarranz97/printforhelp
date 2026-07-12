"""Enums and error codes for the requests domain."""

from enum import StrEnum


class RequestStatus(StrEnum):
    """Lifecycle status shared by Request and RequestItem (FR-040 / FR-121)."""

    OPEN = "open"
    FULFILLED = "fulfilled"
    CLOSED = "closed"


class ModerationStatus(StrEnum):
    """Publication state of a Request, orthogonal to its lifecycle ``status``.

    Only ``APPROVED`` campaigns are public. Everything else is visible solely
    to the effective requesters and to maintainers/admins — enforced in the
    service layer's read gate, not just hidden in the UI.

    ``DRAFT`` is the author still writing it up; ``PENDING`` is queued for
    review; ``CHANGES_REQUESTED`` was sent back with a note; ``REJECTED`` was
    turned down. A rejected or sent-back campaign may be edited and resubmitted
    (back to ``PENDING``), so neither is a dead end.
    """

    DRAFT = "draft"
    PENDING = "pending"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


# States the author may (re)submit for review from.
SUBMITTABLE_STATUSES = (
    ModerationStatus.DRAFT,
    ModerationStatus.CHANGES_REQUESTED,
    ModerationStatus.REJECTED,
)

# Max length of the note a maintainer leaves when asking for more information
# or rejecting a campaign.
MAX_REVIEW_NOTE_LENGTH = 2_000


class HelpState(StrEnum):
    """Derived fulfillment bucket for an item or campaign (progress-based).

    ``needs_help`` still needs more commitments; ``committed`` has enough claimed
    so no more help is needed but delivery/receipt is pending; ``completed`` has
    been received at the center (or is otherwise closed/done).
    """

    NEEDS_HELP = "needs_help"
    COMMITTED = "committed"
    COMPLETED = "completed"


class ClosedReason(StrEnum):
    """System-recorded reason a Request or RequestItem was closed."""

    MANUAL = "manual"
    REQUEST_CLOSED = "request_closed"
    REQUEST_ITEM_CLOSED = "request_item_closed"
    RESOURCE_ARCHIVED = "resource_archived"


class ErrorCode(StrEnum):
    """Error codes raised by the requests domain."""

    REQUEST_NOT_FOUND = "REQUEST_NOT_FOUND"
    REQUEST_ITEM_NOT_FOUND = "REQUEST_ITEM_NOT_FOUND"
    NOT_EFFECTIVE_REQUESTER = "NOT_EFFECTIVE_REQUESTER"
    REQUEST_NOT_OPEN = "REQUEST_NOT_OPEN"
    REQUEST_NOT_CLOSED = "REQUEST_NOT_CLOSED"
    REQUEST_ITEM_NOT_CLOSED = "REQUEST_ITEM_NOT_CLOSED"
    REQUEST_NEEDS_ITEM = "REQUEST_NEEDS_ITEM"
    ITEM_HAS_CONTRIBUTIONS = "ITEM_HAS_CONTRIBUTIONS"
    ITEM_REQUEST_MISMATCH = "ITEM_REQUEST_MISMATCH"
    REQUEST_NOT_SUBMITTABLE = "REQUEST_NOT_SUBMITTABLE"
    REQUEST_NOT_PENDING = "REQUEST_NOT_PENDING"
    REQUEST_NOT_PUBLISHED = "REQUEST_NOT_PUBLISHED"
    REQUEST_NOT_APPROVED = "REQUEST_NOT_APPROVED"
