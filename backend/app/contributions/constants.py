"""Enums, error codes, and tunables for the contributions domain."""

from enum import StrEnum

# A ``claimed`` Contribution that never advances expires after this many
# days (FR-055).
STALE_CLAIM_DAYS = 14


class ContributionStatus(StrEnum):
    """The five-state Contribution lifecycle (FR-052)."""

    CLAIMED = "claimed"
    PREPARED = "prepared"
    DELIVERED = "delivered"
    RECEIVED = "received"
    RELEASED = "released"


class ReleasedReason(StrEnum):
    """Why a Contribution was released (terminal)."""

    MANUAL = "manual"
    EXPIRED = "expired"
    COLLECTION_CENTER_ARCHIVED = "collection_center_archived"
    REQUEST_CLOSED = "request_closed"
    REQUEST_ITEM_CLOSED = "request_item_closed"
    RESOURCE_ARCHIVED = "resource_archived"


class ErrorCode(StrEnum):
    """Error codes raised by the contributions domain."""

    CONTRIBUTION_NOT_FOUND = "CONTRIBUTION_NOT_FOUND"
    NOT_THE_MAKER = "NOT_THE_MAKER"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    NOT_RECEIVER = "NOT_RECEIVER"
    REQUEST_ITEM_NOT_OPEN = "REQUEST_ITEM_NOT_OPEN"
    CENTER_NOT_AVAILABLE = "CENTER_NOT_AVAILABLE"
    CENTER_REQUIRED = "CENTER_REQUIRED"
    CONTRIBUTION_LOCKED = "CONTRIBUTION_LOCKED"
