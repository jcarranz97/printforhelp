"""HTTP routes for in-app notifications and watch subscriptions.

Two routers share this module:

- ``router`` (``/notifications``) — the recipient's own notification list,
  unread count, and mark-read.
- ``watches_router`` (``/watches``) — subscribe / unsubscribe / status for
  a polymorphic entity.

Every route requires an authenticated active user; a user only ever sees
or mutates their own notifications and subscriptions.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.activity.schemas import ActorSummary
from app.database import get_db
from app.dependencies import CurrentActiveUser
from app.users.models import User

from . import models, schemas, service
from .constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/notifications", tags=["notifications"])
watches_router = APIRouter(prefix="/watches", tags=["watches"])

DatabaseDep = Annotated[Session, Depends(get_db)]


def _actor(db: Session, user_id: uuid.UUID) -> ActorSummary:
    """Build an ``ActorSummary`` for a user id (handles missing users)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:  # pragma: no cover - defensive; actors are soft-deleted
        return ActorSummary(id=user_id, username="(unknown)")
    return ActorSummary(id=user.id, username=user.username)


def _notification_response(
    db: Session, notification: models.Notification
) -> schemas.NotificationResponse:
    return schemas.NotificationResponse(
        id=notification.id,
        entity_type=EntityType(notification.entity_type),
        entity_id=notification.entity_id,
        actor=_actor(db, notification.actor_user_id),
        reason=notification.reason,
        event=notification.event,
        comment_id=notification.comment_id,
        title=notification.payload.get("title", ""),
        link=notification.payload.get("link", ""),
        anchor=notification.payload.get("anchor"),
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.get("", response_model=list[schemas.NotificationResponse])
async def list_notifications(
    user: CurrentActiveUser,
    db: DatabaseDep,
    unread_only: Annotated[bool, Query()] = False,
    before: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> list[schemas.NotificationResponse]:
    """The current user's notifications, newest first."""
    rows = service.list_for_user(
        db, user=user, limit=limit, before=before, unread_only=unread_only
    )
    return [_notification_response(db, n) for n in rows]


@router.get("/unread-count", response_model=schemas.UnreadCountResponse)
async def unread_count(
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.UnreadCountResponse:
    """Unread notification count for the avatar badge."""
    return schemas.UnreadCountResponse(count=service.unread_count(db, user=user))


@router.post("/read", response_model=schemas.MarkReadResponse)
async def mark_read(
    payload: schemas.MarkReadRequest,
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.MarkReadResponse:
    """Mark specific notifications (or all unread) as read."""
    updated = service.mark_read(db, user=user, ids=payload.ids, mark_all=payload.all)
    return schemas.MarkReadResponse(updated=updated)


@watches_router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def create_watch(
    payload: schemas.WatchCreate,
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> None:
    """Subscribe the current user to an entity."""
    service.watch_entity(
        db, user=user, entity_type=payload.entity_type, entity_id=payload.entity_id
    )


@watches_router.delete(
    "/{entity_type}/{entity_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_watch(
    entity_type: EntityType,
    entity_id: uuid.UUID,
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> None:
    """Unsubscribe the current user from an entity."""
    service.unwatch_entity(db, user=user, entity_type=entity_type, entity_id=entity_id)


@watches_router.get(
    "/{entity_type}/{entity_id}", response_model=schemas.WatchStatusResponse
)
async def get_watch(
    entity_type: EntityType,
    entity_id: uuid.UUID,
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.WatchStatusResponse:
    """Whether the current user is watching an entity."""
    return schemas.WatchStatusResponse(
        watching=service.is_watching(
            db, user=user, entity_type=entity_type, entity_id=entity_id
        )
    )
