"""Enums and error codes for the organizations domain."""

from enum import StrEnum


class OrganizationStatus(StrEnum):
    """Organization operational status (FR-103)."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class OrganizationRole(StrEnum):
    """Membership roles within an organization (§6.9)."""

    OWNER = "owner"
    MEMBER = "member"


class ErrorCode(StrEnum):
    """Error codes raised by the organizations domain."""

    ORGANIZATION_NOT_FOUND = "ORGANIZATION_NOT_FOUND"
    ORG_NAME_TAKEN = "ORG_NAME_TAKEN"
    ORG_MEMBERSHIP_REQUIRED = "ORG_MEMBERSHIP_REQUIRED"
    NOT_EFFECTIVE_OWNER = "NOT_EFFECTIVE_OWNER"
    ORG_ARCHIVE_BLOCKED = "ORG_ARCHIVE_BLOCKED"
    OWNER_CANNOT_LEAVE = "OWNER_CANNOT_LEAVE"
    NOT_ORG_MEMBER = "NOT_ORG_MEMBER"
