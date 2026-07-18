"""Business logic for the item-tracking (QR provenance) domain.

Owns token generation, the private/group/public visibility gate, record
appends (open to anyone who can view), and owner-only management (visibility,
named members, tag edits). No HTTP concerns live here.
"""

import secrets
from typing import TYPE_CHECKING, NamedTuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.permissions import has_global_override
from app.users.models import User

if TYPE_CHECKING:
    from PIL import Image

    from app.contributions.models import Contribution

from . import models, schemas
from .constants import (
    MAX_TRACKED_UNITS,
    TRACKING_TOKEN_BYTES,
    TrackingTargetKind,
    TrackingVisibility,
)
from .exceptions import (
    ContributorMessageNotFoundExceptionError,
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
) -> tuple[str, str | None, str | None, int | None]:
    """Return ``(name, image_url, label_image_url, labels_per_page)``."""
    from app.requests.models import RequestItem
    from app.resources.models import Resource

    row = (
        db.query(
            Resource.name,
            Resource.image_url,
            Resource.label_image_url,
            Resource.labels_per_page,
        )
        .join(RequestItem, RequestItem.resource_id == Resource.id)
        .filter(RequestItem.id == contribution.request_item_id)
        .first()
    )
    if row is None:  # pragma: no cover - invariant (item always has a resource)
        return "", None, None, None
    return row[0], row[1], row[2], row[3]


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


# --------------------------------------------------------------------------- #
# Watch notifications
# --------------------------------------------------------------------------- #
# A tracking group is a watchable entity (like resources, centers, requests):
# the maker auto-watches when they generate it, any logged-in user can opt in
# from the public page, and every new record fans a notification out to all
# watchers. Imported function-locally to keep the notifications service off the
# module import path (mirrors ``activity.service``).
def _ensure_group_watch(db: Session, user_id: UUID, group_id: UUID) -> None:
    """Idempotently subscribe a user to a tracking group (flush only)."""
    from app.activity.constants import EntityType
    from app.notifications import service as notifications_service

    notifications_service.ensure_watch(db, user_id, EntityType.TRACKING_GROUP, group_id)


def _notify_group_watchers(
    db: Session, group_id: UUID, actor_user_id: UUID, record_id: UUID
) -> None:
    """Fan a new tracking record out to the group's watchers (flush only).

    ``record_id`` becomes a ``record-<id>`` anchor on each notification so a
    click deep-links to and highlights that update on the tracking page.
    """
    from app.activity.constants import EntityType
    from app.notifications import service as notifications_service
    from app.notifications.constants import TRACKING_UPDATE_EVENT

    # Carry the update's note so the email can show it, like a comment body.
    note = (
        db.query(models.TrackingRecord.description)
        .filter(models.TrackingRecord.id == record_id)
        .scalar()
    )
    notifications_service.fan_out_to_watchers(
        db,
        entity_type=EntityType.TRACKING_GROUP,
        entity_id=group_id,
        actor_user_id=actor_user_id,
        event=TRACKING_UPDATE_EVENT,
        anchor=f"record-{record_id}",
        extra_payload={"note": note} if note else None,
    )


def _is_watching_group(db: Session, group_id: UUID, viewer: User | None) -> bool:
    """Whether ``viewer`` is subscribed to a tracking group (False for guests)."""
    if viewer is None:
        return False
    from app.activity.constants import EntityType
    from app.notifications import service as notifications_service

    return notifications_service.is_watching(
        db, user=viewer, entity_type=EntityType.TRACKING_GROUP, entity_id=group_id
    )


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
        # Public by default so owners can share QR codes immediately without
        # first flipping visibility. They can still restrict to group/private.
        visibility=TrackingVisibility.PUBLIC,
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
    # The contribution's maker watches their own tracking by default, so they
    # are notified of every update posted after a QR scan.
    _ensure_group_watch(db, contribution.maker_id, group.id)
    db.commit()
    db.refresh(group)
    return group


def sync_units(db: Session, contribution: "Contribution") -> None:
    """Reconcile a Contribution's per-unit tracking items with its quantity.

    Called when a maker edits the quantity of a Contribution that already has
    a tracking group (a no-op when it has none). Sequence numbers are printed
    on physical labels, so they are treated as stable identities:

    - **Growing** adds items for the new trailing sequences only; every QR
      already printed keeps its token.
    - **Shrinking** *soft-deletes* the surplus trailing items rather than
      dropping them. Their tokens stop resolving (``/track/{token}`` 404s, and
      they leave the QR bundle), but the rows survive — so a maker who shrinks
      and then grows again gets the **same tokens back**, and the labels they
      already printed for those units keep working.

    Staged only (no commit); the caller owns the transaction.
    """
    group = _group_for_contribution(db, contribution.id)
    if group is None:
        return

    target = min(contribution.quantity, MAX_TRACKED_UNITS)
    items = (
        db.query(models.TrackingItem)
        .filter(models.TrackingItem.group_id == group.id)
        .all()
    )
    by_sequence = {item.sequence: item for item in items}

    for item in items:
        item.active = item.sequence <= target
    for sequence in range(1, target + 1):
        if sequence not in by_sequence:
            db.add(
                models.TrackingItem(
                    group_id=group.id,
                    tracking_token=_new_token(),
                    sequence=sequence,
                )
            )
    db.flush()


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
    resource_name, resource_image_url, resource_label_image_url, _ = _resource_context(
        db, contribution
    )
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
        resource_label_image_url=resource_label_image_url,
        members=[
            schemas.TrackingGroupMemberSummary(id=mid, username=username)
            for mid, username in members
        ],
        items=[schemas.TrackingItemResponse.model_validate(item) for item in items],
        records=records,
        watching=_is_watching_group(db, group.id, actor),
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
    resource_name, resource_image_url, _, _ = _resource_context(db, contribution)

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
        group_id=group.id,
        visibility=group.visibility,
        resource_name=resource_name,
        resource_image_url=resource_image_url,
        contribution_status=str(contribution.status),
        quantity=contribution.quantity,
        item_sequence=item.sequence if item is not None else None,
        records=records,
        can_contribute=True,
        watching=_is_watching_group(db, group.id, viewer),
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
    db.flush()
    # Notify everyone watching the group (maker + opted-in users). Guest posts
    # have no user, so they are attributed to the system ``anonymous`` account
    # as the actor (it is never a watcher, so nothing is suppressed).
    if viewer is not None:
        actor_id = viewer.id
    else:
        from app.users.service import get_or_create_anonymous_user

        actor_id = get_or_create_anonymous_user(db).id
    _notify_group_watchers(db, group.id, actor_id, record.id)
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
class BundleContext(NamedTuple):
    """Everything the QR-bundle renderer needs for one group (owner-gated)."""

    group_token: str
    items: list[tuple[int, str]]  # (sequence, token) per unit
    label_image_url: str | None  # the Resource's print label, if any
    labels_per_page: int | None  # creator's labels-per-A4-page (None = auto)


def get_bundle_context(db: Session, group_id: UUID, actor: User) -> BundleContext:
    """Return the group token, item tokens, and label image URL (owner)."""
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
    _, _, label_image_url, labels_per_page = _resource_context(db, contribution)
    return BundleContext(
        group_token=group.tracking_token,
        items=labels,
        label_image_url=label_image_url,
        labels_per_page=labels_per_page,
    )


# --------------------------------------------------------------------------- #
# Saved contributor messages (user-owned reusable templates)
# --------------------------------------------------------------------------- #
def list_contributor_messages(
    db: Session, user: User
) -> list[models.ContributorMessage]:
    """Return the user's saved message templates, newest first."""
    return (
        db.query(models.ContributorMessage)
        .filter(
            models.ContributorMessage.user_id == user.id,
            models.ContributorMessage.active.is_(True),
        )
        .order_by(models.ContributorMessage.created_at.desc())
        .all()
    )


def create_contributor_message(
    db: Session, user: User, body: str
) -> models.ContributorMessage:
    """Save a reusable message for the user (idempotent on identical text).

    An identical active template is returned as-is (no duplicate); a
    previously deleted identical one is reactivated instead of re-inserted.
    """
    text = body.strip()
    existing = (
        db.query(models.ContributorMessage)
        .filter(
            models.ContributorMessage.user_id == user.id,
            models.ContributorMessage.body == text,
        )
        .first()
    )
    if existing is not None:
        if not existing.active:
            existing.active = True
        db.commit()
        db.refresh(existing)
        return existing
    row = models.ContributorMessage(user_id=user.id, body=text)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_contributor_message(db: Session, user: User, message_id: UUID) -> None:
    """Soft-delete one of the user's saved messages (404 if not theirs)."""
    row = (
        db.query(models.ContributorMessage)
        .filter(
            models.ContributorMessage.id == message_id,
            models.ContributorMessage.user_id == user.id,
            models.ContributorMessage.active.is_(True),
        )
        .first()
    )
    if row is None:
        raise ContributorMessageNotFoundExceptionError(message_id)
    row.active = False
    db.commit()


def resolve_bundle_message(message: str | None) -> str:
    """Return the note to print: the maker's, or the default community one."""
    from .constants import DEFAULT_CONTRIBUTOR_MESSAGE

    text = (message or "").strip()
    return text or DEFAULT_CONTRIBUTOR_MESSAGE


def _fetch_label_bytes(url: str) -> bytes | None:
    """Return the raw bytes of a label image URL (local media or remote)."""
    from pathlib import Path

    from app.config import settings

    # Locally hosted uploads: read straight from disk, skipping a needless
    # round-trip back to our own /media mount.
    marker = "/media/"
    if marker in url:
        key = url.split(marker, 1)[1]
        path = Path(settings.MEDIA_ROOT) / key
        if path.is_file():
            return path.read_bytes()
    if url.startswith(("http://", "https://")):
        import httpx

        try:
            # Owner-gated download; a short timeout and size cap bound the
            # server-side fetch of a maker-provided label URL.
            resp = httpx.get(url, timeout=5.0, follow_redirects=True)
        except httpx.HTTPError:
            return None
        ok = resp.status_code == httpx.codes.OK
        if ok and len(resp.content) <= settings.MAX_IMAGE_BYTES:
            return resp.content
    return None


def load_label_image(url: str | None) -> "Image.Image | None":
    """Load a label image URL into a Pillow image, or None if unavailable.

    Never raises: a missing or unreadable label simply drops out of the print
    so the bundle still renders.
    """
    if not url:
        return None
    from io import BytesIO

    from PIL import Image as PILImage, UnidentifiedImageError

    data = _fetch_label_bytes(url)
    if data is None:
        return None
    try:
        return PILImage.open(BytesIO(data)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        return None


def assert_token_exists(db: Session, token: str) -> None:
    """Raise ``TrackingNotFound`` if no active token matches (QR endpoint)."""
    _resolve_token(db, token)
