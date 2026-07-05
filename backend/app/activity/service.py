"""Activity-log and comments business logic.

``record`` is imported by other domains (e.g. shipments) to log their
lifecycle events into the public timeline. It flushes but does not commit
so the event is atomic with the mutation that triggered it. The comment
methods own their own transaction.
"""

import re
import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.notifications.constants import MENTION_PATTERN
from app.permissions import has_global_override
from app.users.models import User

from . import models, validators
from .constants import (
    COMMENTABLE_ENTITY_TYPES,
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

_MENTION_RE = re.compile(MENTION_PATTERN)


def record(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    action: ActivityAction,
    changes: dict[str, Any] | None = None,
    notify_exclude_user_ids: set[uuid.UUID] | None = None,
    anchor: str | None = None,
) -> models.ActivityLog:
    """Stage a public activity row (flush only; caller commits).

    Recording an event is the single choke point every domain already
    calls, so it is also where notifications fan out: watchers of the
    entity get pinged for notifiable actions, and the actor auto-subscribes.
    ``notify_exclude_user_ids`` skips recipients already notified another way
    (e.g. @mention) so they are not double-notified for the same event.
    ``anchor`` is an optional URL fragment (e.g. ``item-<id>``) cached on the
    watch notifications so a click deep-links to and highlights the exact
    element on the target page.
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
        anchor=anchor,
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
    anchor: str | None = None,
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
            anchor=anchor,
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


def latest_activity_at(
    db: Session, *, entity_type: EntityType, entity_id: uuid.UUID
) -> datetime | None:
    """Return the newest activity ``created_at`` for one entity, or ``None``.

    Comments and (via the domains that call ``record``) lifecycle events both
    write activity rows, so this single query is a good "last activity" signal.
    """
    return (
        db.query(func.max(models.ActivityLog.created_at))
        .filter(
            models.ActivityLog.entity_type == entity_type.value,
            models.ActivityLog.entity_id == entity_id,
        )
        .scalar()
    )


def create_comment(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    body: str,
    actor: User,
) -> models.Comment:
    """Post a comment and record a ``commented`` activity event (FR-131)."""
    if entity_type not in COMMENTABLE_ENTITY_TYPES:
        raise InvalidEntityReferenceExceptionError(entity_type.value, entity_id)
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


def _extract_mention_usernames(body: str) -> list[str]:
    """Return the unique @usernames referenced in a comment body, in order."""
    seen: list[str] = []
    for match in _MENTION_RE.finditer(body):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def _active_username_map(db: Session, names: Iterable[str]) -> dict[str, str]:
    """Map lowercased candidate usernames to the real active user's username."""
    lowered = {name.lower() for name in names}
    if not lowered:
        return {}
    rows = (
        db.query(User.username)
        .filter(
            func.lower(User.username).in_(lowered),
            User.active.is_(True),
        )
        .all()
    )
    return {row[0].lower(): row[0] for row in rows}


def resolve_comment_mentions(db: Session, body: str) -> list[str]:
    """Return the valid (real, active) usernames mentioned in one body."""
    candidates = _extract_mention_usernames(body)
    if not candidates:
        return []
    valid = _active_username_map(db, candidates)
    result: list[str] = []
    for name in candidates:
        actual = valid.get(name.lower())
        if actual is not None and actual not in result:
            result.append(actual)
    return result


def resolve_mentions_for_comments(
    db: Session, comments: Sequence[models.Comment]
) -> dict[uuid.UUID, list[str]]:
    """Batch-resolve valid mentions for many comments in a single query."""
    per_comment = {c.id: _extract_mention_usernames(c.body) for c in comments}
    all_names = {name for names in per_comment.values() for name in names}
    valid = _active_username_map(db, all_names)
    out: dict[uuid.UUID, list[str]] = {}
    for comment_id, names in per_comment.items():
        resolved: list[str] = []
        for name in names:
            actual = valid.get(name.lower())
            if actual is not None and actual not in resolved:
                resolved.append(actual)
        out[comment_id] = resolved
    return out


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
