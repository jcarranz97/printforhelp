"""HTTP routes for the public activity feed and comments.

Two routers share this module so the polymorphic entity machinery is in
one place:

- ``activity_router`` (``/activity``) — read-only public timeline.
- ``comments_router`` (``/comments``) — public reads; authenticated
  writes (any logged-in user posts; author edits; author or
  maintainer/admin deletes).
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser, OptionalUser

from . import models, schemas, service, validators
from .constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ActivityAction,
    EntityType,
)

activity_router = APIRouter(prefix="/activity", tags=["activity"])
comments_router = APIRouter(prefix="/comments", tags=["comments"])

DatabaseDep = Annotated[Session, Depends(get_db)]


def _activity_response(
    db: Session, entry: models.ActivityLog
) -> schemas.ActivityResponse:
    return schemas.ActivityResponse(
        id=entry.id,
        entity_type=EntityType(entry.entity_type),
        entity_id=entry.entity_id,
        actor=service.actor_summary(db, entry.actor_user_id),
        action=ActivityAction(entry.action),
        changes=entry.changes,
        created_at=entry.created_at,
    )


def _comment_response(
    db: Session,
    comment: models.Comment,
    mentions: dict[str, str] | None = None,
) -> schemas.CommentResponse:
    return schemas.CommentResponse(
        id=comment.id,
        entity_type=EntityType(comment.entity_type),
        entity_id=comment.entity_id,
        author=service.actor_summary(db, comment.author_user_id),
        parent_comment_id=comment.parent_comment_id,
        body=comment.body,
        edited_at=comment.edited_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        mentions=(
            mentions
            if mentions is not None
            else service.resolve_comment_mentions(db, comment.body)
        ),
    )


@activity_router.get("", response_model=list[schemas.ActivityResponse])
async def list_activity(
    db: DatabaseDep,
    viewer: OptionalUser,
    entity_type: Annotated[EntityType, Query()],
    entity_id: Annotated[uuid.UUID, Query()],
    before: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> list[schemas.ActivityResponse]:
    """Public timeline for one entity, newest first (FR-133).

    An unpublished campaign's timeline is empty to everyone but its requesters
    and maintainers — a pre-publication link must not expose it (FR-134).
    """
    if not validators.is_entity_visible(db, entity_type, entity_id, viewer):
        return []
    entries = service.list_activity(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        before=before,
    )
    return [_activity_response(db, e) for e in entries]


@comments_router.get("", response_model=list[schemas.CommentResponse])
async def list_comments(
    db: DatabaseDep,
    viewer: OptionalUser,
    entity_type: Annotated[EntityType, Query()],
    entity_id: Annotated[uuid.UUID, Query()],
    before: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> list[schemas.CommentResponse]:
    """Public comment list for one entity, newest first (FR-131).

    Hidden for an unpublished campaign, as with the activity feed (FR-134).
    """
    if not validators.is_entity_visible(db, entity_type, entity_id, viewer):
        return []
    comments = service.list_comments(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        before=before,
    )
    mentions_by_id = service.resolve_mentions_for_comments(db, comments)
    return [_comment_response(db, c, mentions_by_id.get(c.id, {})) for c in comments]


@comments_router.post(
    "", response_model=schemas.CommentResponse, status_code=status.HTTP_201_CREATED
)
async def create_comment(
    payload: schemas.CommentCreate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.CommentResponse:
    """Post a Markdown comment (any logged-in user, FR-131)."""
    comment = service.create_comment(
        db,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        body=payload.body,
        actor=actor,
        parent_comment_id=payload.parent_comment_id,
    )
    return _comment_response(db, comment)


@comments_router.patch("/{comment_id}", response_model=schemas.CommentResponse)
async def update_comment(
    comment_id: uuid.UUID,
    payload: schemas.CommentUpdate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.CommentResponse:
    """Edit a comment body (author only, FR-132)."""
    comment = service.get_comment_or_raise(db, comment_id)
    updated = service.update_comment(
        db, comment=comment, body=payload.body, actor=actor
    )
    return _comment_response(db, updated)


@comments_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> None:
    """Soft-delete a comment (author or maintainer/admin, FR-132)."""
    comment = service.get_comment_or_raise(db, comment_id)
    service.delete_comment(db, comment=comment, actor=actor)
