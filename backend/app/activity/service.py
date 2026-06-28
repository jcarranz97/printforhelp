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
) -> models.ActivityLog:
    """Stage a public activity row (flush only; caller commits)."""
    entry = models.ActivityLog(
        entity_type=entity_type.value,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action.value,
        changes=changes or {},
    )
    db.add(entry)
    db.flush()
    return entry


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

    record(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor.id,
        action=ActivityAction.COMMENTED,
        changes={"comment_id": str(comment.id)},
    )

    db.commit()
    db.refresh(comment)
    return comment


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

    comment.body = body
    comment.edited_at = datetime.now(UTC)
    db.flush()

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
