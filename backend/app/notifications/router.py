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

from app.activity import service as activity_service
from app.activity.constants import EntityType
from app.database import get_db
from app.dependencies import CurrentActiveUser

from . import models, schemas, service, unsubscribe
from .constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, NotificationCategory
from .exceptions import UnknownNotificationCategoryExceptionError

router = APIRouter(prefix="/notifications", tags=["notifications"])
watches_router = APIRouter(prefix="/watches", tags=["watches"])

DatabaseDep = Annotated[Session, Depends(get_db)]


def _notification_response(
    db: Session, notification: models.Notification
) -> schemas.NotificationResponse:
    return schemas.NotificationResponse(
        id=notification.id,
        entity_type=EntityType(notification.entity_type),
        entity_id=notification.entity_id,
        actor=activity_service.actor_summary(db, notification.actor_user_id),
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


@router.get("/preferences", response_model=list[schemas.NotificationPreferenceItem])
async def list_preferences(
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> list[schemas.NotificationPreferenceItem]:
    """The current user's per-category in-app / email channel choices."""
    return [
        schemas.NotificationPreferenceItem(
            category=category.value,
            in_app_enabled=in_app,
            email_enabled=email,
        )
        for category, in_app, email in service.list_preferences(db, user=user)
    ]


@router.put(
    "/preferences/{category}", response_model=schemas.NotificationPreferenceItem
)
async def update_preference(
    category: str,
    payload: schemas.NotificationPreferenceUpdate,
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.NotificationPreferenceItem:
    """Set both channels for one category for the current user."""
    try:
        parsed = NotificationCategory(category)
    except ValueError as exc:
        raise UnknownNotificationCategoryExceptionError(category) from exc
    service.set_preference(
        db,
        user=user,
        category=parsed,
        in_app_enabled=payload.in_app_enabled,
        email_enabled=payload.email_enabled,
    )
    return schemas.NotificationPreferenceItem(
        category=parsed.value,
        in_app_enabled=payload.in_app_enabled,
        email_enabled=payload.email_enabled,
    )


@router.get("/unsubscribe/preview", response_model=schemas.UnsubscribePreviewResponse)
async def preview_unsubscribe(
    token: Annotated[str, Query()],
    db: DatabaseDep,
) -> schemas.UnsubscribePreviewResponse:
    """Describe what a (no-login) unsubscribe link will do, for the confirm page."""
    _, action = unsubscribe.parse_unsubscribe_token(token)
    return schemas.UnsubscribePreviewResponse(
        description=unsubscribe.describe_action(db, action)
    )


@router.post("/unsubscribe", response_model=schemas.UnsubscribeResponse)
async def apply_unsubscribe(
    payload: schemas.UnsubscribeRequest,
    db: DatabaseDep,
) -> schemas.UnsubscribeResponse:
    """Apply a signed unsubscribe token. No authentication (email recipients).

    POST (not GET) so inbox link-scanners that prefetch URLs cannot silently
    unsubscribe a user; the frontend confirm page issues the POST on click.
    """
    user_id, action = unsubscribe.parse_unsubscribe_token(payload.token)
    message = unsubscribe.apply_unsubscribe(db, user_id, action)
    return schemas.UnsubscribeResponse(message=message)


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
