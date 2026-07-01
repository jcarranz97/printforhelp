"""Business logic for the item-tracking (QR provenance) domain.

Owns token generation, the private/group/public visibility gate, record
appends (open to anyone who can view), and owner-only management (visibility,
named members, tag edits). No HTTP concerns live here.
"""

import secrets
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.permissions import has_global_override
from app.users.models import User

if TYPE_CHECKING:
    from app.contributions.models import Contribution

from . import models, schemas
from .constants import (
    MAX_TRACKED_UNITS,
    TRACKING_TOKEN_BYTES,
    TrackingTargetKind,
    TrackingVisibility,
)
from .exceptions import (
    RecordEditForbiddenExceptionError,
    RecordNotFoundExceptionError,
    TrackingAlreadyExistsExceptionError,
    TrackingForbiddenExceptionError,
    TrackingNotFoundExceptionError,
)


def _new_token() -> str:
    """Return a fresh unguessable URL-safe tracking token."""
    return secrets.token_urlsafe(TRACKING_TOKEN_BYTES)


def _get_contribution(db: Session, contribution_id: UUID) -> "Contribution":
    """Fetch a Contribution or raise its domain 404."""
    from app.contributions.service import get_or_raise

    return get_or_raise(db, contribution_id)


def _assert_owner(contribution: "Contribution", actor: User) -> None:
    """Require the caller to be the contribution's maker or a maintainer/admin."""
    if contribution.maker_id != actor.id and not has_global_override(actor):
        raise TrackingForbiddenExceptionError


def _resource_context(
    db: Session, contribution: "Contribution"
) -> tuple[str, str | None]:
    """Return ``(resource_name, resource_image_url)`` for a Contribution."""
    from app.requests.models import RequestItem
    from app.resources.models import Resource

    row = (
        db.query(Resource.name, Resource.image_url)
        .join(RequestItem, RequestItem.resource_id == Resource.id)
        .filter(RequestItem.id == contribution.request_item_id)
        .first()
    )
    if row is None:  # pragma: no cover - invariant (item always has a resource)
        return "", None
    return row[0], row[1]


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #
def _get_group_by_id(db: Session, group_id: UUID) -> models.TrackingGroup:
    group = (
        db.query(models.TrackingGroup)
        .filter(
            models.TrackingGroup.id == group_id,
            models.TrackingGroup.active.is_(True),
        )
        .first()
    )
    if group is None:
        raise TrackingNotFoundExceptionError(group_id)
    return group


def _group_for_contribution(
    db: Session, contribution_id: UUID
) -> models.TrackingGroup | None:
    return (
        db.query(models.TrackingGroup)
        .filter(
            models.TrackingGroup.contribution_id == contribution_id,
            models.TrackingGroup.active.is_(True),
        )
        .first()
    )


def _resolve_token(
    db: Session, token: str
) -> tuple[TrackingTargetKind, models.TrackingGroup, models.TrackingItem | None]:
    """Resolve a token to its group (and item, if an item token)."""
    item = (
        db.query(models.TrackingItem)
        .filter(
            models.TrackingItem.tracking_token == token,
            models.TrackingItem.active.is_(True),
        )
        .first()
    )
    if item is not None:
        return TrackingTargetKind.ITEM, _get_group_by_id(db, item.group_id), item

    group = (
        db.query(models.TrackingGroup)
        .filter(
            models.TrackingGroup.tracking_token == token,
            models.TrackingGroup.active.is_(True),
        )
        .first()
    )
    if group is not None:
        return TrackingTargetKind.GROUP, group, None

    raise TrackingNotFoundExceptionError(token)


def _is_group_member(db: Session, group_id: UUID, user_id: UUID) -> bool:
    return (
        db.query(models.TrackingGroupMember.id)
        .filter(
            models.TrackingGroupMember.group_id == group_id,
            models.TrackingGroupMember.user_id == user_id,
            models.TrackingGroupMember.active.is_(True),
        )
        .first()
        is not None
    )


def _can_view(db: Session, group: models.TrackingGroup, viewer: User | None) -> bool:
    """Return whether ``viewer`` may read (and therefore append to) a group."""
    if group.visibility == TrackingVisibility.PUBLIC:
        return True
    if viewer is None:
        return False
    contribution = _get_contribution(db, group.contribution_id)
    if viewer.id == contribution.maker_id or has_global_override(viewer):
        return True
    if group.visibility == TrackingVisibility.GROUP:
        return _is_group_member(db, group.id, viewer.id)
    return False


# --------------------------------------------------------------------------- #
# Response builders
# --------------------------------------------------------------------------- #
def _author(db: Session, record: models.TrackingRecord) -> schemas.TrackingRecordAuthor:
    """Public author summary, honoring the anonymous-display flag."""
    if record.display_anonymous or record.author_user_id is None:
        return schemas.TrackingRecordAuthor(id=None, username=None)
    user = db.get(User, record.author_user_id)
    if user is None:  # pragma: no cover - users are soft-deleted, never removed
        return schemas.TrackingRecordAuthor(id=None, username=None)
    return schemas.TrackingRecordAuthor(id=user.id, username=user.username)


def _can_edit_record(
    record: models.TrackingRecord, viewer: User | None, maker_id: UUID
) -> bool:
    if viewer is None:
        return False
    return viewer.id in (record.author_user_id, maker_id) or has_global_override(viewer)


def build_record_response(
    db: Session,
    record: models.TrackingRecord,
    *,
    kind: TrackingTargetKind,
    token: str,
    viewer: User | None,
    maker_id: UUID,
    item_sequence: int | None = None,
) -> schemas.TrackingRecordResponse:
    """Build the public/owner response for one record (with edit permission)."""
    return schemas.TrackingRecordResponse(
        id=record.id,
        target_kind=kind,
        target_token=token,
        item_sequence=item_sequence,
        author=_author(db, record),
        description=record.description,
        tags=list(record.tags),
        created_at=record.created_at,
        can_edit_tags=_can_edit_record(record, viewer, maker_id),
    )


# --------------------------------------------------------------------------- #
# Owner operations
# --------------------------------------------------------------------------- #
def generate_tracking(
    db: Session, contribution_id: UUID, actor: User
) -> models.TrackingGroup:
    """Create the tracking group + one item per unit for a Contribution."""
    contribution = _get_contribution(db, contribution_id)
    _assert_owner(contribution, actor)
    if _group_for_contribution(db, contribution.id) is not None:
        raise TrackingAlreadyExistsExceptionError(contribution.id)

    units = min(contribution.quantity, MAX_TRACKED_UNITS)
    group = models.TrackingGroup(
        contribution_id=contribution.id,
        tracking_token=_new_token(),
        visibility=TrackingVisibility.PRIVATE,
    )
    db.add(group)
    db.flush()
    for sequence in range(1, units + 1):
        db.add(
            models.TrackingItem(
                group_id=group.id,
                tracking_token=_new_token(),
                sequence=sequence,
            )
        )
    db.commit()
    db.refresh(group)
    return group


def _resolve_usernames(db: Session, usernames: list[str]) -> list[User]:
    """Resolve usernames to active users, case-insensitively (skip unknown)."""
    names = {n.strip().casefold() for n in usernames if n.strip()}
    if not names:
        return []
    return (
        db.query(User)
        .filter(func.lower(User.username).in_(names), User.active.is_(True))
        .all()
    )


def update_group(
    db: Session,
    group_id: UUID,
    actor: User,
    payload: schemas.TrackingUpdate,
) -> models.TrackingGroup:
    """Set visibility and replace the named group-visibility members."""
    group = _get_group_by_id(db, group_id)
    contribution = _get_contribution(db, group.contribution_id)
    _assert_owner(contribution, actor)

    group.visibility = payload.visibility

    new_users = _resolve_usernames(db, payload.member_usernames)
    new_ids = {u.id for u in new_users}
    existing = (
        db.query(models.TrackingGroupMember)
        .filter(models.TrackingGroupMember.group_id == group.id)
        .all()
    )
    existing_ids = {m.user_id for m in existing}
    for member in existing:
        member.active = member.user_id in new_ids
    for user in new_users:
        if user.id not in existing_ids:
            db.add(models.TrackingGroupMember(group_id=group.id, user_id=user.id))

    db.commit()
    db.refresh(group)
    return group


def get_owner_view(
    db: Session, contribution_id: UUID, actor: User
) -> schemas.OwnerTrackingResponse:
    """Return the full owner-facing tracking view for a Contribution."""
    contribution = _get_contribution(db, contribution_id)
    _assert_owner(contribution, actor)
    group = _group_for_contribution(db, contribution.id)
    if group is None:
        raise TrackingNotFoundExceptionError(contribution.id)

    items = (
        db.query(models.TrackingItem)
        .filter(
            models.TrackingItem.group_id == group.id,
            models.TrackingItem.active.is_(True),
        )
        .order_by(models.TrackingItem.sequence)
        .all()
    )
    token_by_item = {item.id: item.tracking_token for item in items}
    seq_by_item = {item.id: item.sequence for item in items}
    item_ids = list(token_by_item)

    target_conditions = [models.TrackingRecord.tracking_group_id == group.id]
    if item_ids:
        target_conditions.append(models.TrackingRecord.tracking_item_id.in_(item_ids))

    members = (
        db.query(User.id, User.username)
        .join(
            models.TrackingGroupMember,
            models.TrackingGroupMember.user_id == User.id,
        )
        .filter(
            models.TrackingGroupMember.group_id == group.id,
            models.TrackingGroupMember.active.is_(True),
        )
        .order_by(func.lower(User.username))
        .all()
    )

    record_rows = (
        db.query(models.TrackingRecord)
        .filter(
            models.TrackingRecord.active.is_(True),
            or_(*target_conditions),
        )
        .order_by(models.TrackingRecord.created_at.desc())
        .all()
    )
    resource_name, resource_image_url = _resource_context(db, contribution)
    records: list[schemas.TrackingRecordResponse] = []
    for record in record_rows:
        if record.tracking_group_id is not None:
            kind, token, sequence = TrackingTargetKind.GROUP, group.tracking_token, None
        else:
            assert record.tracking_item_id is not None
            item_id = record.tracking_item_id
            kind, token = TrackingTargetKind.ITEM, token_by_item[item_id]
            sequence = seq_by_item[item_id]
        records.append(
            build_record_response(
                db,
                record,
                kind=kind,
                token=token,
                viewer=actor,
                maker_id=contribution.maker_id,
                item_sequence=sequence,
            )
        )

    return schemas.OwnerTrackingResponse(
        group_id=group.id,
        contribution_id=contribution.id,
        tracking_token=group.tracking_token,
        visibility=group.visibility,
        quantity=contribution.quantity,
        resource_name=resource_name,
        resource_image_url=resource_image_url,
        members=[
            schemas.TrackingGroupMemberSummary(id=mid, username=username)
            for mid, username in members
        ],
        items=[schemas.TrackingItemResponse.model_validate(item) for item in items],
        records=records,
    )


# --------------------------------------------------------------------------- #
# Public operations
# --------------------------------------------------------------------------- #
def _group_timeline(
    db: Session,
    group: models.TrackingGroup,
    viewer: User | None,
    maker_id: UUID,
    include_item_updates: bool,
) -> list[schemas.TrackingRecordResponse]:
    """Build a group token's timeline, optionally folding in item updates.

    Each record keeps its own target: group records carry the group token,
    item records carry their item token and unit sequence, so the timeline can
    label which unit an update belongs to.
    """
    token_by_item: dict[UUID, str] = {}
    seq_by_item: dict[UUID, int] = {}
    conditions = [models.TrackingRecord.tracking_group_id == group.id]

    if include_item_updates:
        items = (
            db.query(models.TrackingItem)
            .filter(
                models.TrackingItem.group_id == group.id,
                models.TrackingItem.active.is_(True),
            )
            .all()
        )
        token_by_item = {i.id: i.tracking_token for i in items}
        seq_by_item = {i.id: i.sequence for i in items}
        if token_by_item:
            conditions.append(
                models.TrackingRecord.tracking_item_id.in_(list(token_by_item))
            )

    record_rows = (
        db.query(models.TrackingRecord)
        .filter(
            models.TrackingRecord.active.is_(True),
            or_(*conditions),
        )
        .order_by(models.TrackingRecord.created_at.desc())
        .all()
    )

    records: list[schemas.TrackingRecordResponse] = []
    for record in record_rows:
        if record.tracking_group_id is not None:
            r_kind, r_token, r_seq = (
                TrackingTargetKind.GROUP,
                group.tracking_token,
                None,
            )
        else:
            item_id = record.tracking_item_id
            assert item_id is not None
            r_kind, r_token, r_seq = (
                TrackingTargetKind.ITEM,
                token_by_item[item_id],
                seq_by_item[item_id],
            )
        records.append(
            build_record_response(
                db,
                record,
                kind=r_kind,
                token=r_token,
                viewer=viewer,
                maker_id=maker_id,
                item_sequence=r_seq,
            )
        )
    return records


def get_public_view(
    db: Session,
    token: str,
    viewer: User | None,
    include_item_updates: bool = True,
) -> schemas.PublicTrackingResponse:
    """Resolve a token and return its visibility-gated timeline.

    On a **group** token, ``include_item_updates`` (default) folds every
    per-item update into the group timeline as well; set it False to show only
    the group-level updates. Ignored for an item token (always that item only).
    """
    kind, group, item = _resolve_token(db, token)
    if not _can_view(db, group, viewer):
        raise TrackingForbiddenExceptionError
    contribution = _get_contribution(db, group.contribution_id)
    resource_name, resource_image_url = _resource_context(db, contribution)

    if kind == TrackingTargetKind.ITEM and item is not None:
        record_rows = (
            db.query(models.TrackingRecord)
            .filter(
                models.TrackingRecord.tracking_item_id == item.id,
                models.TrackingRecord.active.is_(True),
            )
            .order_by(models.TrackingRecord.created_at.desc())
            .all()
        )
        records = [
            build_record_response(
                db,
                record,
                kind=kind,
                token=token,
                viewer=viewer,
                maker_id=contribution.maker_id,
                item_sequence=item.sequence,
            )
            for record in record_rows
        ]
    else:
        records = _group_timeline(
            db, group, viewer, contribution.maker_id, include_item_updates
        )

    return schemas.PublicTrackingResponse(
        target_kind=kind,
        tracking_token=token,
        visibility=group.visibility,
        resource_name=resource_name,
        resource_image_url=resource_image_url,
        contribution_status=str(contribution.status),
        quantity=contribution.quantity,
        item_sequence=item.sequence if item is not None else None,
        records=records,
        can_contribute=True,
    )


def add_record(
    db: Session,
    token: str,
    viewer: User | None,
    payload: schemas.RecordCreate,
) -> tuple[TrackingTargetKind, UUID, models.TrackingRecord, int | None]:
    """Append a record to a token's timeline (gated by visibility).

    Returns the target kind, the contribution's maker id, the new record, and
    the item sequence (for an item token) so the router can render the
    response with edit permissions resolved.
    """
    kind, group, item = _resolve_token(db, token)
    if not _can_view(db, group, viewer):
        raise TrackingForbiddenExceptionError
    contribution = _get_contribution(db, group.contribution_id)

    record = models.TrackingRecord(
        tracking_group_id=group.id if kind == TrackingTargetKind.GROUP else None,
        tracking_item_id=item.id if item is not None else None,
        author_user_id=viewer.id if viewer is not None else None,
        # Guests are always anonymous; a logged-in author chooses per post.
        display_anonymous=payload.display_anonymous if viewer is not None else True,
        description=payload.description,
        tags=payload.tags,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return (
        kind,
        contribution.maker_id,
        record,
        (item.sequence if item is not None else None),
    )


def _get_record(db: Session, record_id: UUID) -> models.TrackingRecord:
    record = (
        db.query(models.TrackingRecord)
        .filter(
            models.TrackingRecord.id == record_id,
            models.TrackingRecord.active.is_(True),
        )
        .first()
    )
    if record is None:
        raise RecordNotFoundExceptionError(record_id)
    return record


def _contribution_for_record(
    db: Session, record: models.TrackingRecord
) -> tuple[models.TrackingGroup, "Contribution"]:
    if record.tracking_group_id is not None:
        group = _get_group_by_id(db, record.tracking_group_id)
    else:
        assert record.tracking_item_id is not None
        item = (
            db.query(models.TrackingItem)
            .filter(models.TrackingItem.id == record.tracking_item_id)
            .first()
        )
        assert item is not None
        group = _get_group_by_id(db, item.group_id)
    return group, _get_contribution(db, group.contribution_id)


def edit_record_tags(
    db: Session,
    record_id: UUID,
    actor: User,
    tags: list[str],
) -> tuple[models.TrackingRecord, TrackingTargetKind, str, UUID, int | None]:
    """Replace a record's tags (author / contribution owner / maintainer)."""
    record = _get_record(db, record_id)
    group, contribution = _contribution_for_record(db, record)
    if not _can_edit_record(record, actor, contribution.maker_id):
        raise RecordEditForbiddenExceptionError

    record.tags = tags
    db.commit()
    db.refresh(record)

    sequence: int | None = None
    if record.tracking_group_id is not None:
        kind, token = TrackingTargetKind.GROUP, group.tracking_token
    else:
        item = (
            db.query(models.TrackingItem)
            .filter(models.TrackingItem.id == record.tracking_item_id)
            .first()
        )
        assert item is not None
        kind, token, sequence = (
            TrackingTargetKind.ITEM,
            item.tracking_token,
            item.sequence,
        )
    return record, kind, token, contribution.maker_id, sequence


# --------------------------------------------------------------------------- #
# QR helpers
# --------------------------------------------------------------------------- #
def get_group_tokens(
    db: Session, group_id: UUID, actor: User
) -> tuple[str, list[tuple[int, str]]]:
    """Return the group token and each item's ``(sequence, token)`` (owner)."""
    group = _get_group_by_id(db, group_id)
    contribution = _get_contribution(db, group.contribution_id)
    _assert_owner(contribution, actor)
    items = (
        db.query(models.TrackingItem)
        .filter(
            models.TrackingItem.group_id == group.id,
            models.TrackingItem.active.is_(True),
        )
        .order_by(models.TrackingItem.sequence)
        .all()
    )
    labels = [(item.sequence, item.tracking_token) for item in items]
    return group.tracking_token, labels


def assert_token_exists(db: Session, token: str) -> None:
    """Raise ``TrackingNotFound`` if no active token matches (QR endpoint)."""
    _resolve_token(db, token)
