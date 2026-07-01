"""Activity-log and comments business logic.

``record`` is imported by other domains (e.g. shipments) to log their
lifecycle events into the public timeline. It flushes but does not commit
so the event is atomic with the mutation that triggered it. The comment
methods own their own transaction.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.permissions import has_global_override
from app.users.models import User

from . import models, validators
from .constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ActivityAction,
    EntityType,
)
from .exceptions import (
    CommentDeleteForbiddenExceptionError,
    CommentNotAuthorExceptionError,
    CommentNotFoundExceptionError,
    InvalidEntityReferenceExceptionError,
)


def record(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    action: ActivityAction,
    changes: dict[str, Any] | None = None,
    notify_exclude_user_ids: set[uuid.UUID] | None = None,
) -> models.ActivityLog:
    """Stage a public activity row (flush only; caller commits).

    Recording an event is the single choke point every domain already
    calls, so it is also where notifications fan out: watchers of the
    entity get pinged for notifiable actions, and the actor auto-subscribes.
    ``notify_exclude_user_ids`` skips recipients already notified another way
    (e.g. @mention) so they are not double-notified for the same event.
    """
    entry = models.ActivityLog(
        entity_type=entity_type.value,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action.value,
        changes=changes or {},
    )
    db.add(entry)
    db.flush()
    _dispatch_notifications(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action,
        changes=changes,
        notify_exclude_user_ids=notify_exclude_user_ids,
    )
    return entry


def _dispatch_notifications(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    action: ActivityAction,
    changes: dict[str, Any] | None,
    notify_exclude_user_ids: set[uuid.UUID] | None,
) -> None:
    """Fan a recorded event out to watchers and auto-subscribe the actor.

    Imported function-locally to break the activity <-> notifications import
    cycle (the notifications service reads activity models/validators).
    """
    from app.notifications import service as notifications_service
    from app.notifications.constants import AUTO_WATCH_ACTIONS, NOTIFY_ACTIONS

    if action in NOTIFY_ACTIONS:
        comment_id_raw = (changes or {}).get("comment_id")
        comment_id = uuid.UUID(comment_id_raw) if comment_id_raw else None
        notifications_service.fan_out_to_watchers(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            event=action.value,
            comment_id=comment_id,
            exclude_user_ids=notify_exclude_user_ids,
        )
    if action in AUTO_WATCH_ACTIONS:
        notifications_service.ensure_watch(db, actor_user_id, entity_type, entity_id)


def list_activity(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    limit: int = DEFAULT_PAGE_SIZE,
    before: datetime | None = None,
) -> list[models.ActivityLog]:
    """Return public activity rows for one entity, newest first."""
    limit = min(limit, MAX_PAGE_SIZE)
    query = db.query(models.ActivityLog).filter(
        models.ActivityLog.entity_type == entity_type.value,
        models.ActivityLog.entity_id == entity_id,
    )
    if before is not None:
        query = query.filter(models.ActivityLog.created_at < before)
    return query.order_by(desc(models.ActivityLog.created_at)).limit(limit).all()


def create_comment(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    body: str,
    actor: User,
) -> models.Comment:
    """Post a comment and record a ``commented`` activity event (FR-131)."""
    if not validators.entity_exists(db, entity_type, entity_id):
        raise InvalidEntityReferenceExceptionError(entity_type.value, entity_id)

    comment = models.Comment(
        entity_type=entity_type.value,
        entity_id=entity_id,
        author_user_id=actor.id,
        body=body,
    )
    db.add(comment)
    db.flush()

    mentioned = _notify_mentions(db, comment=comment, actor=actor)

    record(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor.id,
        action=ActivityAction.COMMENTED,
        changes={"comment_id": str(comment.id)},
        notify_exclude_user_ids=mentioned,
    )

    db.commit()
    db.refresh(comment)
    return comment


def _notify_mentions(
    db: Session,
    *,
    comment: models.Comment,
    actor: User,
    previous_body: str | None = None,
) -> set[uuid.UUID]:
    """Create @mention notifications for a comment; return notified ids.

    On an edit, ``previous_body`` suppresses re-notifying users who were
    already mentioned. Function-local import breaks the
    activity <-> notifications cycle.
    """
    from app.notifications import service as notifications_service

    return notifications_service.create_mention_notifications(
        db, comment=comment, actor=actor, previous_body=previous_body
    )


def get_comment_or_raise(db: Session, comment_id: uuid.UUID) -> models.Comment:
    """Return an active comment by id or raise ``COMMENT_NOT_FOUND``."""
    comment = (
        db.query(models.Comment)
        .filter(
            models.Comment.id == comment_id,
            models.Comment.active.is_(True),
        )
        .first()
    )
    if comment is None:
        raise CommentNotFoundExceptionError(comment_id)
    return comment


def update_comment(
    db: Session,
    *,
    comment: models.Comment,
    body: str,
    actor: User,
) -> models.Comment:
    """Edit a comment body. Author only (FR-132)."""
    if comment.author_user_id != actor.id:
        raise CommentNotAuthorExceptionError

    previous_body = comment.body
    comment.body = body
    comment.edited_at = datetime.now(UTC)
    db.flush()

    _notify_mentions(db, comment=comment, actor=actor, previous_body=previous_body)

    record(
        db,
        entity_type=EntityType(comment.entity_type),
        entity_id=comment.entity_id,
        actor_user_id=actor.id,
        action=ActivityAction.COMMENT_EDITED,
        changes={"comment_id": str(comment.id)},
    )

    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, *, comment: models.Comment, actor: User) -> None:
    """Soft-delete a comment. Author or maintainer/admin (FR-132)."""
    if comment.author_user_id != actor.id and not has_global_override(actor):
        raise CommentDeleteForbiddenExceptionError

    comment.active = False
    db.flush()

    record(
        db,
        entity_type=EntityType(comment.entity_type),
        entity_id=comment.entity_id,
        actor_user_id=actor.id,
        action=ActivityAction.COMMENT_DELETED,
        changes={"comment_id": str(comment.id)},
    )

    db.commit()


def list_comments(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    limit: int = DEFAULT_PAGE_SIZE,
    before: datetime | None = None,
) -> list[models.Comment]:
    """Return active comments for one entity, newest first (public)."""
    limit = min(limit, MAX_PAGE_SIZE)
    query = db.query(models.Comment).filter(
        models.Comment.entity_type == entity_type.value,
        models.Comment.entity_id == entity_id,
        models.Comment.active.is_(True),
    )
    if before is not None:
        query = query.filter(models.Comment.created_at < before)
    return query.order_by(desc(models.Comment.created_at)).limit(limit).all()
