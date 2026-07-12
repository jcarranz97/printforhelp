"""Watch-subscription and in-app notification business logic.

Notifications are fanned out from a single choke point: the activity
``record`` function calls :func:`fan_out_to_watchers` (for lifecycle and
comment events) and :func:`ensure_watch` (to auto-subscribe the actor),
while :func:`create_mention_notifications` handles ``@username`` mentions
parsed from comment bodies. The write helpers used inside that flow flush
only -- the mutation that triggered them owns the commit -- so a
notification is atomic with the event that produced it. The router-facing
watch / mark-read helpers own their own transaction.

In-app only for v1; the unused ``emailed_at`` column and the
reason / event split are the forward hooks for a future opt-in email
digest.
"""

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.activity import validators
from app.activity.constants import EntityType
from app.activity.models import Comment
from app.collection_centers.models import CollectionCenter
from app.contributions.models import Contribution
from app.requests.models import Request, RequestItem
from app.resources.models import Resource
from app.shipments.models import Shipment
from app.tracking.models import TrackingGroup
from app.users.constants import UserRole
from app.users.models import User
from app.users.service import get_user_by_username

from . import models
from .constants import (
    DEFAULT_PAGE_SIZE,
    MAX_MENTIONS_PER_COMMENT,
    MAX_PAGE_SIZE,
    MENTION_EVENT,
    MENTION_PATTERN,
    NotificationReason,
)
from .exceptions import (
    InvalidMarkReadRequestExceptionError,
    InvalidWatchTargetExceptionError,
)

_MENTION_RE = re.compile(MENTION_PATTERN)


# --------------------------------------------------------------------------
# Watch subscriptions
# --------------------------------------------------------------------------


def _active_watch(
    db: Session,
    user_id: uuid.UUID,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> models.Watch | None:
    """Return the active Watch row for (user, entity), or None."""
    return (
        db.query(models.Watch)
        .filter(
            models.Watch.user_id == user_id,
            models.Watch.entity_type == entity_type.value,
            models.Watch.entity_id == entity_id,
            models.Watch.active.is_(True),
        )
        .first()
    )


def ensure_watch(
    db: Session,
    user_id: uuid.UUID,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> None:
    """Idempotently subscribe a user to an entity (flush only).

    Reactivates a previously unwatched row instead of inserting a duplicate,
    keeping at most one row per (user, entity).
    """
    existing = (
        db.query(models.Watch)
        .filter(
            models.Watch.user_id == user_id,
            models.Watch.entity_type == entity_type.value,
            models.Watch.entity_id == entity_id,
        )
        .first()
    )
    if existing is not None:
        if not existing.active:
            existing.active = True
            db.flush()
        return
    db.add(
        models.Watch(
            user_id=user_id,
            entity_type=entity_type.value,
            entity_id=entity_id,
        )
    )
    db.flush()


def watch_entity(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> None:
    """Manually subscribe via the API; validates the target exists and is visible.

    The visibility check matters for a Request's private review thread (and for
    an unpublished campaign): without it a stranger could subscribe and learn
    from the notifications alone that a conversation is happening, even though
    they can never read it.
    """
    if not validators.entity_exists(db, entity_type, entity_id):
        raise InvalidWatchTargetExceptionError(entity_type.value, entity_id)
    if not validators.is_entity_visible(db, entity_type, entity_id, user):
        raise InvalidWatchTargetExceptionError(entity_type.value, entity_id)
    ensure_watch(db, user.id, entity_type, entity_id)
    db.commit()


def unwatch_entity(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> None:
    """Soft-delete the user's subscription to an entity (no-op if absent)."""
    watch = _active_watch(db, user.id, entity_type, entity_id)
    if watch is not None:
        watch.active = False
        db.commit()


def is_watching(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> bool:
    """Return True if the user has an active subscription to the entity."""
    return _active_watch(db, user.id, entity_type, entity_id) is not None


# --------------------------------------------------------------------------
# Notification fan-out
# --------------------------------------------------------------------------


def fan_out_to_watchers(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    event: str,
    comment_id: uuid.UUID | None = None,
    exclude_user_ids: set[uuid.UUID] | None = None,
    anchor: str | None = None,
) -> None:
    """Create one watch notification per active watcher (flush only).

    The actor and any ``exclude_user_ids`` (e.g. users already notified by
    an @mention for the same comment) are skipped, as are inactive accounts.
    ``anchor`` is an optional URL fragment (e.g. ``record-<id>``) cached on
    the notification so a click deep-links to and highlights the exact item
    on the target page (the same treatment @mention/comment notifications get
    from ``comment_id``).
    """
    excluded = {actor_user_id}
    if exclude_user_ids:
        excluded |= exclude_user_ids
    watcher_ids = {
        row[0]
        for row in db.query(models.Watch.user_id)
        .filter(
            models.Watch.entity_type == entity_type.value,
            models.Watch.entity_id == entity_id,
            models.Watch.active.is_(True),
        )
        .all()
    }
    recipients = watcher_ids - excluded
    if not recipients:
        return
    active_recipient_ids = {
        row[0]
        for row in db.query(User.id)
        .filter(User.id.in_(recipients), User.active.is_(True))
        .all()
    }
    if not active_recipient_ids:
        return
    title, link = _resolve_link_and_title(db, entity_type, entity_id)
    payload: dict[str, str] = {"title": title, "link": link}
    if anchor is not None:
        payload["anchor"] = anchor
    for recipient_id in active_recipient_ids:
        db.add(
            models.Notification(
                recipient_user_id=recipient_id,
                actor_user_id=actor_user_id,
                entity_type=entity_type.value,
                entity_id=entity_id,
                reason=NotificationReason.WATCH.value,
                event=event,
                comment_id=comment_id,
                # Each row gets its own dict so the JSONB column is never
                # aliased across notifications.
                payload=dict(payload),
            )
        )
    db.flush()


def fan_out_to_users(
    db: Session,
    *,
    recipient_ids: set[uuid.UUID],
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    event: str,
    reason: NotificationReason = NotificationReason.MODERATION,
) -> None:
    """Notify an explicit set of users, bypassing the watch list (flush only).

    Used by flows where the recipients are determined by role or ownership
    rather than by subscription — the moderation queue, where maintainers must
    hear about a submission they never opted into, and the author must hear the
    verdict. The actor is skipped (no self-notifications), as are inactive
    accounts.
    """
    recipients = recipient_ids - {actor_user_id}
    if not recipients:
        return
    active_recipient_ids = {
        row[0]
        for row in db.query(User.id)
        .filter(User.id.in_(recipients), User.active.is_(True))
        .all()
    }
    if not active_recipient_ids:
        return
    title, link = _resolve_link_and_title(db, entity_type, entity_id)
    for recipient_id in active_recipient_ids:
        db.add(
            models.Notification(
                recipient_user_id=recipient_id,
                actor_user_id=actor_user_id,
                entity_type=entity_type.value,
                entity_id=entity_id,
                reason=reason.value,
                event=event,
                # Each row gets its own dict so the JSONB column is never
                # aliased across notifications.
                payload={"title": title, "link": link},
            )
        )
    db.flush()


def maintainer_user_ids(db: Session) -> set[uuid.UUID]:
    """Return the ids of every active maintainer/admin (the review audience)."""
    return {
        row[0]
        for row in db.query(User.id)
        .filter(
            User.role.in_([UserRole.MAINTAINER, UserRole.ADMIN]),
            User.active.is_(True),
        )
        .all()
    }


def create_mention_notifications(
    db: Session,
    *,
    comment: Comment,
    actor: User,
    previous_body: str | None = None,
) -> set[uuid.UUID]:
    """Notify users named with @username in a comment body (flush only).

    Returns the set of notified recipient ids so the caller can exclude them
    from the watcher fan-out and avoid double-notifying. On an edit,
    ``previous_body`` suppresses users who were already mentioned before the
    edit, so only newly added mentions are pinged.
    """
    usernames = _extract_mentions(comment.body)
    if previous_body is not None:
        already = {name.lower() for name in _extract_mentions(previous_body)}
        usernames = [name for name in usernames if name.lower() not in already]
    if not usernames:
        return set()
    entity_type = EntityType(comment.entity_type)
    title, link = _resolve_link_and_title(db, entity_type, comment.entity_id)
    notified: set[uuid.UUID] = set()
    for username in usernames:
        user = get_user_by_username(db, username)
        if user is None or not user.active:
            continue
        if user.id == actor.id or user.id in notified:
            continue
        db.add(
            models.Notification(
                recipient_user_id=user.id,
                actor_user_id=actor.id,
                entity_type=comment.entity_type,
                entity_id=comment.entity_id,
                reason=NotificationReason.MENTION.value,
                event=MENTION_EVENT,
                comment_id=comment.id,
                payload={"title": title, "link": link},
            )
        )
        notified.add(user.id)
    if notified:
        db.flush()
    return notified


def _extract_mentions(body: str) -> list[str]:
    """Return up to ``MAX_MENTIONS_PER_COMMENT`` unique @usernames, in order."""
    seen: list[str] = []
    for match in _MENTION_RE.finditer(body):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
        if len(seen) >= MAX_MENTIONS_PER_COMMENT:
            break
    return seen


def _resolve_link_and_title(
    db: Session,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> tuple[str, str]:
    """Build a display title + frontend link for a notification target.

    Resolved once at creation; falls back to a generic title if the entity
    was since removed. The shipment link is nested under its parent center.
    """
    if entity_type is EntityType.COLLECTION_CENTER:
        center = (
            db.query(CollectionCenter).filter(CollectionCenter.id == entity_id).first()
        )
        title = center.name if center is not None else "Collection center"
        return title, f"/centers/{entity_id}"
    if entity_type is EntityType.RESOURCE:
        resource = db.query(Resource).filter(Resource.id == entity_id).first()
        title = resource.name if resource is not None else "Resource"
        return title, f"/parts/{entity_id}"
    if entity_type in (EntityType.REQUEST, EntityType.REQUEST_REVIEW):
        request = db.query(Request).filter(Request.id == entity_id).first()
        title = request.title if request is not None else "Request"
        # Both live on the campaign page; the review thread is an anchor on it.
        anchor = "#review" if entity_type is EntityType.REQUEST_REVIEW else ""
        return title, f"/requests/{entity_id}{anchor}"
    if entity_type is EntityType.REQUEST_ITEM:
        return _request_item_link_and_title(db, entity_id)
    if entity_type is EntityType.TRACKING_GROUP:
        return _tracking_link_and_title(db, entity_id)
    return _shipment_link_and_title(db, entity_id)


def _shipment_link_and_title(db: Session, entity_id: uuid.UUID) -> tuple[str, str]:
    """Build a title + center-nested link for a shipment notification target."""
    shipment = db.query(Shipment).filter(Shipment.id == entity_id).first()
    if shipment is None:
        return "Shipment", "/centers"
    title = shipment.destination or "Shipment"
    return title, f"/centers/{shipment.collection_center_id}/shipments/{entity_id}"


def _request_item_link_and_title(db: Session, item_id: uuid.UUID) -> tuple[str, str]:
    """Build a title (Resource name) + link for a request-item timeline.

    The link is nested under the parent Request so it matches the item detail
    page route (``/requests/{request_id}/items/{item_id}``).
    """
    row = (
        db.query(Resource.name, RequestItem.request_id, RequestItem.item_number)
        .select_from(RequestItem)
        .join(Resource, Resource.id == RequestItem.resource_id)
        .filter(RequestItem.id == item_id)
        .first()
    )
    if row is None:  # pragma: no cover - item is soft-deleted, never removed
        return "Request item", "/requests"
    name, request_id, item_number = row
    return (
        name or "Request item",
        f"/requests/{request_id}/items/{item_number}",
    )


def _tracking_link_and_title(db: Session, group_id: uuid.UUID) -> tuple[str, str]:
    """Build a title + public ``/track`` link for a tracking group.

    The title reuses the tracked Contribution's Resource name so a tracking
    notification reads like the entity it belongs to; the link points at the
    public QR timeline via the group's share token. Imported locally to keep
    the tracking timeline's Resource name.
    """
    group = db.query(TrackingGroup).filter(TrackingGroup.id == group_id).first()
    if group is None:  # pragma: no cover - group is soft-deleted, never removed
        return "Tracking", "/track"
    name = (
        db.query(Resource.name)
        .select_from(TrackingGroup)
        .join(Contribution, Contribution.id == TrackingGroup.contribution_id)
        .join(RequestItem, RequestItem.id == Contribution.request_item_id)
        .join(Resource, Resource.id == RequestItem.resource_id)
        .filter(TrackingGroup.id == group_id)
        .scalar()
    )
    return (name or "Tracking"), f"/track/{group.tracking_token}"


# --------------------------------------------------------------------------
# Reads + mark-read
# --------------------------------------------------------------------------


def list_for_user(
    db: Session,
    *,
    user: User,
    limit: int = DEFAULT_PAGE_SIZE,
    before: datetime | None = None,
    unread_only: bool = False,
) -> list[models.Notification]:
    """Return the user's notifications, newest first."""
    limit = min(limit, MAX_PAGE_SIZE)
    query = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == user.id,
        models.Notification.active.is_(True),
    )
    if unread_only:
        query = query.filter(models.Notification.read_at.is_(None))
    if before is not None:
        query = query.filter(models.Notification.created_at < before)
    return query.order_by(desc(models.Notification.created_at)).limit(limit).all()


def unread_count(db: Session, *, user: User) -> int:
    """Count the user's unread notifications (powers the badge)."""
    return (
        db.query(func.count(models.Notification.id))
        .filter(
            models.Notification.recipient_user_id == user.id,
            models.Notification.active.is_(True),
            models.Notification.read_at.is_(None),
        )
        .scalar()
    ) or 0


def mark_read(
    db: Session,
    *,
    user: User,
    ids: list[uuid.UUID] | None = None,
    mark_all: bool = False,
) -> int:
    """Mark the given notifications (or all unread) as read; returns count."""
    if not mark_all and not ids:
        raise InvalidMarkReadRequestExceptionError
    query = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == user.id,
        models.Notification.active.is_(True),
        models.Notification.read_at.is_(None),
    )
    if not mark_all:
        query = query.filter(models.Notification.id.in_(ids or []))
    updated = query.update(
        {models.Notification.read_at: datetime.now(UTC)},
        synchronize_session=False,
    )
    db.commit()
    return updated
