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
from app.contributions.models import Contribution
from app.notifications import service as notifications_service
from app.notifications.constants import REACTION_EVENT, NotificationReason
from app.permissions import (
    effective_owner_user_ids,
    effective_requester_user_ids,
)
from app.requests.models import Request, RequestItem
from app.resources.models import Resource
from app.shipments.models import Shipment
from app.tracking.models import TrackingGroup, TrackingItem, TrackingRecord
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
) -> dict[uuid.UUID, tuple[int, bool, bool]]:
    """Batch read of ``(count, reacted, by_author)`` for many entities of a type.

    Powers the comment feed and the tracking timeline, where every visible
    entry needs its like state in one round trip. ``by_author`` is the
    Instagram-style "liked by the author" flag — see :func:`_by_author_ids` for
    who counts as the author of each type; it is ``False`` everywhere else.
    Non-visible or non-reactable entities are masked to ``(0, False, False)``.
    """
    result: dict[uuid.UUID, tuple[int, bool, bool]] = dict.fromkeys(
        entity_ids, (0, False, False)
    )
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
    by_author_ids = _by_author_ids(db, entity_type, visible)
    for eid in visible:
        result[eid] = (counts.get(eid, 0), eid in reacted_ids, eid in by_author_ids)
    return result


def _by_author_ids(
    db: Session, entity_type: EntityType, entity_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Return the entities their own "author" reacted to.

    Who the author is depends on whose space the entry sits in: for a comment
    it is the owner of the parent the comment hangs off (the part's owner, the
    campaign's requester, ...); for a tracking update it is the **maker of the
    tracked Contribution** — the timeline is theirs, so their heart on an
    update is the one worth calling out. Every other reactable type is its own
    author's, so the flag is meaningless there and stays empty.
    """
    if entity_type is EntityType.COMMENT:
        return _liked_by_author_ids(db, entity_ids)
    if entity_type is EntityType.TRACKING_RECORD:
        return _liked_by_maker_ids(db, entity_ids)
    return set()


def _liked_by_maker_ids(db: Session, record_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Return the tracking updates the tracked Contribution's maker reacted to.

    One join resolves every record to its maker (a record hangs off either the
    group or one of its items), then one query checks which of those makers
    actually liked their own record.
    """
    maker_by_record: dict[uuid.UUID, uuid.UUID] = {
        row[0]: row[1]
        for row in db.query(TrackingRecord.id, Contribution.maker_id)
        .select_from(TrackingRecord)
        .outerjoin(TrackingItem, TrackingItem.id == TrackingRecord.tracking_item_id)
        .join(
            TrackingGroup,
            TrackingGroup.id
            == func.coalesce(TrackingRecord.tracking_group_id, TrackingItem.group_id),
        )
        .join(Contribution, Contribution.id == TrackingGroup.contribution_id)
        .filter(TrackingRecord.id.in_(record_ids), TrackingRecord.active.is_(True))
        .all()
    }
    if not maker_by_record:
        return set()
    liked: set[tuple[uuid.UUID, uuid.UUID]] = {
        (row[0], row[1])
        for row in db.query(models.Reaction.entity_id, models.Reaction.user_id)
        .filter(
            models.Reaction.entity_type == EntityType.TRACKING_RECORD.value,
            models.Reaction.entity_id.in_(maker_by_record.keys()),
            models.Reaction.user_id.in_(set(maker_by_record.values())),
            models.Reaction.reaction_type == DEFAULT_REACTION_TYPE,
            models.Reaction.active.is_(True),
        )
        .all()
    }
    return {
        rid for rid, maker_id in maker_by_record.items() if (rid, maker_id) in liked
    }


def _liked_by_author_ids(db: Session, comment_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Return the comments an effective owner of their parent reacted to.

    "Author" here is the owner of the thing the comment hangs off — the part's
    owner, the campaign's requester, the center's owner, etc. Comments on the
    same parent share one owner lookup, so this stays a couple of queries for a
    whole feed.
    """
    rows = (
        db.query(Comment.id, Comment.entity_type, Comment.entity_id)
        .filter(Comment.id.in_(comment_ids), Comment.active.is_(True))
        .all()
    )
    owner_cache: dict[tuple[str, uuid.UUID], set[uuid.UUID]] = {}
    comment_owners: dict[uuid.UUID, set[uuid.UUID]] = {}
    all_owner_ids: set[uuid.UUID] = set()
    for cid, ptype, pid in rows:
        key = (ptype, pid)
        if key not in owner_cache:
            owner_cache[key] = _reaction_recipients(db, EntityType(ptype), pid)
        comment_owners[cid] = owner_cache[key]
        all_owner_ids |= owner_cache[key]
    if not all_owner_ids:
        return set()
    liked_by: dict[uuid.UUID, set[uuid.UUID]] = {}
    for eid, uid in (
        db.query(models.Reaction.entity_id, models.Reaction.user_id)
        .filter(
            models.Reaction.entity_type == EntityType.COMMENT.value,
            models.Reaction.entity_id.in_(comment_ids),
            models.Reaction.user_id.in_(all_owner_ids),
            models.Reaction.reaction_type == DEFAULT_REACTION_TYPE,
            models.Reaction.active.is_(True),
        )
        .all()
    ):
        liked_by.setdefault(eid, set()).add(uid)
    return {
        cid for cid in comment_owners if comment_owners[cid] & liked_by.get(cid, set())
    }


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
    anchor = None
    if entity_type is EntityType.COMMENT:
        anchor = f"comment-{entity_id}"
    elif entity_type is EntityType.TRACKING_RECORD:
        # The tracking timeline already deep-links updates by `record-<id>`.
        anchor = f"record-{entity_id}"
    # Cache the running like total so the email/in-app copy can show "❤ N"
    # without a second lookup at render time.
    like_count = _count(db, entity_type, entity_id)
    extra_payload = {"like_count": str(like_count)}
    if entity_type is EntityType.TRACKING_RECORD:
        # A tracking update has no ``comment_id`` to render from, so carry its
        # text as a note and the email shows it in the same card a comment gets.
        note = (
            db.query(TrackingRecord.description)
            .filter(TrackingRecord.id == entity_id)
            .scalar()
        )
        if note:
            extra_payload["note"] = note
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
        extra_payload=extra_payload,
    )


def _reaction_recipients(  # noqa: PLR0911, C901 - one branch per reactable type
    db: Session, entity_type: EntityType, entity_id: uuid.UUID
) -> set[uuid.UUID]:
    """Resolve who "owns" the reacted-to content and should hear about a like."""
    if entity_type is EntityType.COMMENT:
        comment = db.query(Comment).filter(Comment.id == entity_id).first()
        return {comment.author_user_id} if comment is not None else set()
    if entity_type is EntityType.TRACKING_RECORD:
        # Whoever wrote the update, even when it displays anonymously — the
        # notification goes *to* them, so it reveals nothing. Guest updates
        # carry no author and therefore notify nobody.
        record = db.query(TrackingRecord).filter(TrackingRecord.id == entity_id).first()
        if record is None or record.author_user_id is None:
            return set()
        return {record.author_user_id}
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
