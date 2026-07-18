"""Pydantic request/response models for the notifications domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.activity.constants import EntityType
from app.activity.schemas import ActorSummary


class WatchCreate(BaseModel):
    """Payload for subscribing to an entity."""

    entity_type: EntityType
    entity_id: UUID


class WatchStatusResponse(BaseModel):
    """Whether the current user is watching an entity."""

    watching: bool


class NotificationResponse(BaseModel):
    """A single in-app notification as returned to its recipient."""

    id: UUID
    entity_type: EntityType
    entity_id: UUID
    actor: ActorSummary
    reason: str
    event: str
    comment_id: UUID | None
    title: str
    link: str
    # Optional URL fragment (e.g. ``record-<id>``) to deep-link to and
    # highlight the exact item on the target page. ``None`` for notifications
    # that only point at the entity as a whole.
    anchor: str | None
    read_at: datetime | None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    """Unread notification count for the badge."""

    count: int


class MarkReadRequest(BaseModel):
    """Mark specific notifications read, or all of them."""

    ids: list[UUID] | None = None
    all: bool = False


class MarkReadResponse(BaseModel):
    """How many notifications were marked read."""

    updated: int


class NotificationPreferenceItem(BaseModel):
    """One category's in-app / email channel choice for the current user."""

    category: str
    in_app_enabled: bool
    email_enabled: bool


class NotificationPreferenceUpdate(BaseModel):
    """Payload to set both channels for one category."""

    in_app_enabled: bool
    email_enabled: bool


class UnsubscribeRequest(BaseModel):
    """A signed unsubscribe token, applied without authentication."""

    token: str


class UnsubscribePreviewResponse(BaseModel):
    """A human-readable summary of what an unsubscribe link will do."""

    description: str


class UnsubscribeResponse(BaseModel):
    """Confirmation message after an unsubscribe action was applied."""

    message: str
