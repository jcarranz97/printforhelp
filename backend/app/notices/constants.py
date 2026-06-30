"""Enums and error codes for the notices domain."""

from enum import StrEnum

# Language a notice falls back to when the page's selected locale has no
# translation. English is the recommended baseline for every notice.
DEFAULT_NOTICE_LANGUAGE = "en"


class NoticeSeverity(StrEnum):
    """Visual severity of a site notice (drives the banner styling)."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


class NoticeStatus(StrEnum):
    """Moderation lifecycle of a notice (FR-027-style approval gate)."""

    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class NoticeTargetType(StrEnum):
    """Entity a notice can be attached to in *entity mode*.

    The value is stored as plain text (mirrors ``audit_log.target_type``)
    so a new targetable entity needs no schema migration.
    """

    RESOURCE = "resource"
    COLLECTION_CENTER = "collection_center"
    REQUEST = "request"


class PageScope(StrEnum):
    """Page a *page-mode* notice can target. ``ALL`` shows everywhere."""

    ALL = "all"
    HOME = "home"
    CENTERS = "centers"
    REQUESTS = "requests"
    PARTS = "parts"
    MY_CONTRIBUTIONS = "my_contributions"
    ABOUT = "about"


class ErrorCode(StrEnum):
    """Error codes raised by the notices domain."""

    NOTICE_NOT_FOUND = "NOTICE_NOT_FOUND"
    NOT_ENTITY_OWNER = "NOT_ENTITY_OWNER"
    INVALID_NOTICE_MODE = "INVALID_NOTICE_MODE"
    TRANSLATIONS_REQUIRED = "TRANSLATIONS_REQUIRED"
    DUPLICATE_LANGUAGE = "DUPLICATE_LANGUAGE"
    NOTICE_NOT_PENDING = "NOTICE_NOT_PENDING"
