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
