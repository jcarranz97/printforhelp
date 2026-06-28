"""Enums and error codes for the collection centers domain."""

from enum import StrEnum


class CollectionCenterStatus(StrEnum):
    """Collection Center operational status (FR-033)."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class CollectionCenterRole(StrEnum):
    """Per-center membership role (§6.7).

    Only ``contributor`` exists today; the owner lives on the Center
    entity itself, not in the membership table. Kept as an enum for
    forward extensibility.
    """

    CONTRIBUTOR = "contributor"


class ErrorCode(StrEnum):
    """Error codes raised by the collection centers domain."""

    COLLECTION_CENTER_NOT_FOUND = "COLLECTION_CENTER_NOT_FOUND"
    NOT_EFFECTIVE_OWNER = "NOT_EFFECTIVE_OWNER"
    NOT_EFFECTIVE_MEMBER = "NOT_EFFECTIVE_MEMBER"
    CC_ARCHIVE_BLOCKED = "CC_ARCHIVE_BLOCKED"
    NOT_CONTRIBUTOR = "NOT_CONTRIBUTOR"
