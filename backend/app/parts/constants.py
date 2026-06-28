"""Enums and error codes for the parts domain."""

from enum import StrEnum


class PartStatus(StrEnum):
    """Catalog status of a Part (FR-075)."""

    ACTIVE = "active"
    DISCONTINUED = "discontinued"


class ErrorCode(StrEnum):
    """Error codes raised by the parts domain."""

    PART_NOT_FOUND = "PART_NOT_FOUND"
    NOT_EFFECTIVE_OWNER = "NOT_EFFECTIVE_OWNER"
    PART_ARCHIVE_BLOCKED = "PART_ARCHIVE_BLOCKED"
    PART_DISCONTINUED = "PART_DISCONTINUED"
