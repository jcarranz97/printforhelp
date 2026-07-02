"""Enums and constants for the activity-feed and comments domain.

The activity log and comments are both **polymorphic**: an ``entity_type``
+ ``entity_id`` pair identifies the target without a foreign-key
constraint, so the same two tables cover every domain. Collection Centers,
Shipments, Resources, and Requests opt in (FR-133); more entities can join
later without a schema change.
"""

from enum import StrEnum


class EntityType(StrEnum):
    """Entity types that can be watched or carry public activity (FR-133).

    The first four also accept public comments and an activity timeline.
    ``TRACKING_GROUP`` is **watch-only**: it reuses the polymorphic watch /
    notification plumbing so users can subscribe to a QR tracking timeline,
    but it is not commentable and has no public activity feed.
    """

    COLLECTION_CENTER = "collection_center"
    SHIPMENT = "shipment"
    RESOURCE = "resource"
    REQUEST = "request"
    REQUEST_ITEM = "request_item"
    TRACKING_GROUP = "tracking_group"


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


# Entity types that accept user-authored comments and a public activity
# timeline (FR-131). Tracking groups are watchable but not commentable, so
# they are intentionally excluded.
COMMENTABLE_ENTITY_TYPES: frozenset[EntityType] = frozenset(
    {
        EntityType.COLLECTION_CENTER,
        EntityType.SHIPMENT,
        EntityType.RESOURCE,
        EntityType.REQUEST,
        EntityType.REQUEST_ITEM,
    }
)

MAX_COMMENT_BODY_LENGTH = 10_000
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
