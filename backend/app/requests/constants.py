"""Enums and error codes for the requests domain."""

from enum import StrEnum


class RequestStatus(StrEnum):
    """Lifecycle status shared by Request and RequestItem (FR-040 / FR-121)."""

    OPEN = "open"
    FULFILLED = "fulfilled"
    CLOSED = "closed"


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
