"""Enums and constants for the activity-feed and comments domain.

The activity log and comments are both **polymorphic**: an ``entity_type``
+ ``entity_id`` pair identifies the target without a foreign-key
constraint, so the same two tables cover every domain. Collection Centers,
Shipments, Resources, and Requests opt in (FR-133); more entities can join
later without a schema change.
"""

from enum import StrEnum


class EntityType(StrEnum):
    """Entity types that can carry public activity and comments (FR-133)."""

    COLLECTION_CENTER = "collection_center"
    SHIPMENT = "shipment"
    RESOURCE = "resource"
    REQUEST = "request"


class ActivityAction(StrEnum):
    """Semantic events recorded in the public activity timeline."""

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    DELETED = "deleted"
    COMMENTED = "commented"
    COMMENT_EDITED = "comment_edited"
    COMMENT_DELETED = "comment_deleted"


class ErrorCode(StrEnum):
    """Error codes raised by the activity / comments domain."""

    COMMENT_NOT_FOUND = "COMMENT_NOT_FOUND"
    COMMENT_NOT_AUTHOR = "COMMENT_NOT_AUTHOR"
    COMMENT_DELETE_FORBIDDEN = "COMMENT_DELETE_FORBIDDEN"
    INVALID_ENTITY_REFERENCE = "INVALID_ENTITY_REFERENCE"


# Entity types that accept user-authored comments (FR-131).
COMMENTABLE_ENTITY_TYPES: frozenset[EntityType] = frozenset(EntityType)

MAX_COMMENT_BODY_LENGTH = 10_000
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
