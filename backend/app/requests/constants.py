"""Enums and error codes for the requests domain."""

from enum import StrEnum


class RequestStatus(StrEnum):
    """Lifecycle status shared by Request and RequestItem (FR-040 / FR-121)."""

    OPEN = "open"
    FULFILLED = "fulfilled"
    CLOSED = "closed"


class ClosedReason(StrEnum):
    """System-recorded reason a Request or RequestItem was closed."""

    MANUAL = "manual"
    REQUEST_CLOSED = "request_closed"
    REQUEST_ITEM_CLOSED = "request_item_closed"
    PART_ARCHIVED = "part_archived"


class ErrorCode(StrEnum):
    """Error codes raised by the requests domain."""

    REQUEST_NOT_FOUND = "REQUEST_NOT_FOUND"
    REQUEST_ITEM_NOT_FOUND = "REQUEST_ITEM_NOT_FOUND"
    NOT_EFFECTIVE_REQUESTER = "NOT_EFFECTIVE_REQUESTER"
    REQUEST_NOT_OPEN = "REQUEST_NOT_OPEN"
    REQUEST_NEEDS_ITEM = "REQUEST_NEEDS_ITEM"
    ITEM_HAS_CONTRIBUTIONS = "ITEM_HAS_CONTRIBUTIONS"
    ITEM_REQUEST_MISMATCH = "ITEM_REQUEST_MISMATCH"
    DUPLICATE_PART = "DUPLICATE_PART"
