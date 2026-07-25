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


# States a Collection Center can confirm receipt from. FR-056 only named
# ``delivered``, but the center holding the package is ground truth that it
# arrived, and makers routinely forget to tap through "prepared"/"delivered"
# first — most often the center scans the tracking QR and finds the units still
# sitting in an earlier state. Receipt is therefore accepted from any live
# pre-receipt state and backfills the timestamps that were skipped.
RECEIVABLE_STATUSES = (
    ContributionStatus.CLAIMED,
    ContributionStatus.PREPARED,
    ContributionStatus.DELIVERED,
)


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
