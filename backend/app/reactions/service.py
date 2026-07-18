"""Reactions ("likes") business logic.

React / unreact own their transaction and validate the target exists and is
visible before writing, mirroring the watch flow. Reads return only an
aggregate ``(count, reacted)`` per entity — never who reacted — and mask
entities the viewer cannot see so a like-count can never confirm the existence
of a hidden campaign or private comment.

Creating a *new* reaction fans a notification out to the content's owner or
author ("someone liked your …"), gated by the recipient's ``reaction``
notification preference. Re-reacting to a row that is already active is a
no-op and does not re-notify.
"""

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.activity import validators
from app.activity.constants import REACTABLE_ENTITY_TYPES, EntityType
from app.activity.models import Comment
from app.collection_centers.models import CollectionCenter
from app.notifications import service as notifications_service
from app.notifications.constants import REACTION_EVENT, NotificationReason
from app.permissions import (
    effective_owner_user_ids,
    effective_requester_user_ids,
)
from app.requests.models import Request, RequestItem
from app.resources.models import Resource
from app.shipments.models import Shipment
from app.users.models import User

from . import models
from .constants import DEFAULT_REACTION_TYPE
from .exceptions import InvalidReactionTargetExceptionError


def _active_reaction(
    db: Session,
    user_id: uuid.UUID,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> models.Reaction | None:
    """Return the user's active reaction row for an entity, or None."""
    return (
        db.query(models.Reaction)
        .filter(
            models.Reaction.user_id == user_id,
            models.Reaction.entity_type == entity_type.value,
            models.Reaction.entity_id == entity_id,
            models.Reaction.reaction_type == DEFAULT_REACTION_TYPE,
            models.Reaction.active.is_(True),
        )
        .first()
    )


def _count(db: Session, entity_type: EntityType, entity_id: uuid.UUID) -> int:
    """Count active reactions on one entity."""
    return (
        db.query(func.count(models.Reaction.id)).filter(
            models.Reaction.entity_type == entity_type.value,
            models.Reaction.entity_id == entity_id,
            models.Reaction.active.is_(True),
        )
    ).scalar() or 0


def _state(
    db: Session,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    viewer: User | None,
) -> tuple[int, bool]:
    """Return ``(count, reacted)`` for one visible entity (masked otherwise)."""
    if entity_type not in REACTABLE_ENTITY_TYPES:
        return 0, False
    if not validators.is_entity_visible(db, entity_type, entity_id, viewer):
        return 0, False
    count = _count(db, entity_type, entity_id)
    reacted = (
        viewer is not None
        and _active_reaction(db, viewer.id, entity_type, entity_id) is not None
    )
    return count, reacted


def get_state(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    viewer: User | None,
) -> tuple[int, bool]:
    """Public read of one entity's ``(count, reacted)`` for the viewer."""
    return _state(db, entity_type, entity_id, viewer)


def get_states(
    db: Session,
    *,
    entity_type: EntityType,
    entity_ids: list[uuid.UUID],
    viewer: User | None,
) -> dict[uuid.UUID, tuple[int, bool]]:
    """Batch read of ``(count, reacted)`` for many entities of one type.

    Powers the comment feed, where every visible comment needs its like state
    in one round trip. Non-visible or non-reactable entities are masked to
    ``(0, False)``. Two queries total regardless of how many ids are asked for.
    """
    result: dict[uuid.UUID, tuple[int, bool]] = dict.fromkeys(entity_ids, (0, False))
    if entity_type not in REACTABLE_ENTITY_TYPES or not entity_ids:
        return result
    visible = [
        eid
        for eid in entity_ids
        if validators.is_entity_visible(db, entity_type, eid, viewer)
    ]
    if not visible:
        return result
    counts = {
        row[0]: row[1]
        for row in db.query(models.Reaction.entity_id, func.count(models.Reaction.id))
        .filter(
            models.Reaction.entity_type == entity_type.value,
            models.Reaction.entity_id.in_(visible),
            models.Reaction.active.is_(True),
        )
        .group_by(models.Reaction.entity_id)
        .all()
    }
    reacted_ids: set[uuid.UUID] = set()
    if viewer is not None:
        reacted_ids = {
            row[0]
            for row in db.query(models.Reaction.entity_id)
            .filter(
                models.Reaction.user_id == viewer.id,
                models.Reaction.entity_type == entity_type.value,
                models.Reaction.entity_id.in_(visible),
                models.Reaction.reaction_type == DEFAULT_REACTION_TYPE,
                models.Reaction.active.is_(True),
            )
            .all()
        }
    for eid in visible:
        result[eid] = (counts.get(eid, 0), eid in reacted_ids)
    return result


def react(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> tuple[int, bool]:
    """Add the user's reaction to an entity (idempotent). Returns new state.

    Validates the target is reactable, exists, and is visible to the user —
    an invisible entity is indistinguishable from a missing one. Reactivates a
    previously removed reaction rather than inserting a duplicate. Only a fresh
    activation notifies the content's owner/author; re-reacting is a no-op.
    """
    if entity_type not in REACTABLE_ENTITY_TYPES:
        raise InvalidReactionTargetExceptionError(entity_type.value, entity_id)
    if not validators.entity_exists(db, entity_type, entity_id):
        raise InvalidReactionTargetExceptionError(entity_type.value, entity_id)
    if not validators.is_entity_visible(db, entity_type, entity_id, user):
        raise InvalidReactionTargetExceptionError(entity_type.value, entity_id)

    existing = (
        db.query(models.Reaction)
        .filter(
            models.Reaction.user_id == user.id,
            models.Reaction.entity_type == entity_type.value,
            models.Reaction.entity_id == entity_id,
            models.Reaction.reaction_type == DEFAULT_REACTION_TYPE,
        )
        .first()
    )
    newly_reacted = False
    if existing is None:
        db.add(
            models.Reaction(
                user_id=user.id,
                entity_type=entity_type.value,
                entity_id=entity_id,
                reaction_type=DEFAULT_REACTION_TYPE,
            )
        )
        newly_reacted = True
    elif not existing.active:
        existing.active = True
        newly_reacted = True
    db.flush()

    if newly_reacted:
        _notify_reaction(db, actor=user, entity_type=entity_type, entity_id=entity_id)

    db.commit()
    return _count(db, entity_type, entity_id), True


def unreact(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> tuple[int, bool]:
    """Soft-delete the user's reaction to an entity (no-op if absent)."""
    reaction = _active_reaction(db, user.id, entity_type, entity_id)
    if reaction is not None:
        reaction.active = False
        db.commit()
    return _count(db, entity_type, entity_id), False


def _notify_reaction(
    db: Session,
    *,
    actor: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> None:
    """Notify the reacted-to content's owner/author (flush only).

    Recipients are role/ownership-based, not subscription-based, so the fan-out
    goes through :func:`fan_out_to_users`. The actor is skipped automatically
    (no self-notification). For a comment, the notification deep-links to the
    comment on its parent page via ``comment_id`` / a ``comment-<id>`` anchor.
    """
    recipients = _reaction_recipients(db, entity_type, entity_id)
    if not recipients:
        return
    comment_id = entity_id if entity_type is EntityType.COMMENT else None
    anchor = f"comment-{entity_id}" if entity_type is EntityType.COMMENT else None
    notifications_service.fan_out_to_users(
        db,
        recipient_ids=recipients,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor.id,
        event=REACTION_EVENT,
        reason=NotificationReason.WATCH,
        comment_id=comment_id,
        anchor=anchor,
    )


def _reaction_recipients(  # noqa: PLR0911 - one branch per reactable entity type
    db: Session, entity_type: EntityType, entity_id: uuid.UUID
) -> set[uuid.UUID]:
    """Resolve who "owns" the reacted-to content and should hear about a like."""
    if entity_type is EntityType.COMMENT:
        comment = db.query(Comment).filter(Comment.id == entity_id).first()
        return {comment.author_user_id} if comment is not None else set()
    if entity_type is EntityType.RESOURCE:
        resource = db.query(Resource).filter(Resource.id == entity_id).first()
        return effective_owner_user_ids(db, resource) if resource else set()
    if entity_type is EntityType.REQUEST:
        request = db.query(Request).filter(Request.id == entity_id).first()
        return effective_requester_user_ids(db, request) if request else set()
    if entity_type is EntityType.REQUEST_ITEM:
        item = db.query(RequestItem).filter(RequestItem.id == entity_id).first()
        if item is None:
            return set()
        request = db.query(Request).filter(Request.id == item.request_id).first()
        return effective_requester_user_ids(db, request) if request else set()
    if entity_type is EntityType.COLLECTION_CENTER:
        center = (
            db.query(CollectionCenter).filter(CollectionCenter.id == entity_id).first()
        )
        return effective_owner_user_ids(db, center) if center else set()
    if entity_type is EntityType.SHIPMENT:
        shipment = db.query(Shipment).filter(Shipment.id == entity_id).first()
        if shipment is None:
            return set()
        center = (
            db.query(CollectionCenter)
            .filter(CollectionCenter.id == shipment.collection_center_id)
            .first()
        )
        return effective_owner_user_ids(db, center) if center else set()
    return set()  # pragma: no cover - all reactable types handled above
