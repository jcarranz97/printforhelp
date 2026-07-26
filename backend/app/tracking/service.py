"""Business logic for the item-tracking (QR provenance) domain.

Owns token generation, the private/group/public visibility gate, record
appends (open to anyone who can view), and owner-only management (visibility,
named members, tag edits). No HTTP concerns live here.
"""

from typing import TYPE_CHECKING, Any, NamedTuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.permissions import has_global_override
from app.users.models import User

if TYPE_CHECKING:
    from PIL import Image

    from app.contributions.models import Contribution
    from app.shipments.models import Shipment

from . import models, schemas, tokens
from .constants import (
    MAX_TRACKED_UNITS,
    QR_GROUP_CAPTION,
    RecordOriginLevel,
    TrackingTargetKind,
    TrackingVisibility,
)
from .exceptions import (
    ContributorMessageNotFoundExceptionError,
    InvalidUnitRangeExceptionError,
    RecordEditForbiddenExceptionError,
    RecordNotFoundExceptionError,
    TrackingAlreadyExistsExceptionError,
    TrackingForbiddenExceptionError,
    TrackingNotFoundExceptionError,
)


def _new_token() -> str:
    """Return a fresh unguessable URL-safe tracking token.

    Thin alias kept so the many call sites below read unchanged; the minting
    itself lives in :mod:`app.tracking.tokens`, which the shipments domain also
    imports without dragging this module (and its cycles) along.
    """
    return tokens.new_token()


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


class ResolvedToken(NamedTuple):
    """What a scanned token turned out to be.

    Exactly one of ``item`` / ``shipment`` is set, or neither for a package
    token. ``group`` is populated for unit and package tokens and ``None`` for
    a box, which has no single Contribution behind it.
    """

    kind: TrackingTargetKind
    group: models.TrackingGroup | None
    item: models.TrackingItem | None
    shipment: "Shipment | None"


def _resolve_token(db: Session, token: str) -> ResolvedToken:
    """Resolve a public token to a unit, a package, or a box.

    Ordered smallest-first so the hot path — a unit QR, the most numerous kind
    by far — still costs one indexed lookup. A box token is the rarest and pays
    three.
    """
    item = (
        db.query(models.TrackingItem)
        .filter(
            models.TrackingItem.tracking_token == token,
            models.TrackingItem.active.is_(True),
        )
        .first()
    )
    if item is not None:
        return ResolvedToken(
            TrackingTargetKind.ITEM, _get_group_by_id(db, item.group_id), item, None
        )

    group = (
        db.query(models.TrackingGroup)
        .filter(
            models.TrackingGroup.tracking_token == token,
            models.TrackingGroup.active.is_(True),
        )
        .first()
    )
    if group is not None:
        return ResolvedToken(TrackingTargetKind.GROUP, group, None, None)

    from app.shipments.models import Shipment as ShipmentModel

    shipment = (
        db.query(ShipmentModel)
        .filter(
            ShipmentModel.tracking_token == token,
            ShipmentModel.active.is_(True),
        )
        .first()
    )
    if shipment is not None:
        return ResolvedToken(TrackingTargetKind.SHIPMENT, None, None, shipment)

    raise TrackingNotFoundExceptionError(token)


def _ancestor_shipment_ids(
    db: Session,
    *,
    group_id: UUID | None = None,
    shipment_id: UUID | None = None,
) -> list[UUID]:
    """Boxes enclosing this package or box, innermost first.

    The graph itself lives in the shipments domain; tracking is a consumer.
    Empty for anything not currently packed, which is the common case.
    """
    from app.shipments import service as shipments_service

    return shipments_service.ancestor_shipment_ids(
        db, tracking_group_id=group_id, shipment_id=shipment_id
    )


class _BoxFacts(NamedTuple):
    """The bits of a box a timeline entry needs to name where it came from."""

    token: str
    label: str


def _box_facts(db: Session, shipment_ids: list[UUID]) -> dict[UUID, _BoxFacts]:
    """Batch-load the display facts for a set of boxes (no N+1 on a timeline)."""
    if not shipment_ids:
        return {}
    from app.shipments import service as shipments_service
    from app.shipments.models import Shipment as ShipmentModel

    rows = db.query(ShipmentModel).filter(ShipmentModel.id.in_(shipment_ids)).all()
    return {
        row.id: _BoxFacts(
            token=row.tracking_token,
            label=shipments_service.destination_label(db, row),
        )
        for row in rows
    }


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


def can_view_group(
    db: Session, group: models.TrackingGroup, viewer: User | None
) -> bool:
    """Public wrapper over the visibility tier, for other domains.

    The shipments domain calls this to decide which manifest lines a scanner
    may see: a box is public, but a ``private`` package inside it must not
    become readable just because someone photographed the box.
    """
    return _can_view(db, group, viewer)


def group_for_record(
    db: Session, record: models.TrackingRecord
) -> models.TrackingGroup | None:
    """Resolve the group a record hangs off — directly, or through its item.

    ``None`` for a **box** update, which belongs to a shipment and has no one
    Contribution behind it. Callers must handle that before treating a missing
    group as "not visible" — see :func:`can_view_record`.
    """
    if record.shipment_id is not None:
        return None
    group_id = record.tracking_group_id
    if group_id is None:
        item = db.get(models.TrackingItem, record.tracking_item_id)
        if item is None:  # pragma: no cover - items are soft-deleted, never removed
            return None
        group_id = item.group_id
    return db.get(models.TrackingGroup, group_id)


def can_view_record(
    db: Session, record: models.TrackingRecord, viewer: User | None
) -> bool:
    """Whether ``viewer`` may read one update, via its group's visibility tier.

    The reaction domain calls this so liking an update is gated exactly like
    reading it: a private timeline's updates must not leak a like count.

    A **box** update is public, like the box itself (FR-130/146) — it describes
    where a shipment is, never what is inside it — so it short-circuits to True
    instead of failing the group lookup and silently hiding its like count.
    """
    if record.shipment_id is not None:
        return True
    group = group_for_record(db, record)
    return group is not None and _can_view(db, group, viewer)


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
    origin_level: RecordOriginLevel | None = None,
    origin_shipment_id: UUID | None = None,
    origin_label: str | None = None,
    inherited: bool = False,
) -> schemas.TrackingRecordResponse:
    """Build the public/owner response for one record (with edit permission).

    ``origin_*`` and ``inherited`` describe where the entry was posted relative
    to the page showing it, so a box update reading "left Caracas today" can be
    badged as coming from the box rather than mistaken for the maker's own
    note. They default to matching ``kind``, so existing callers are unchanged.
    """
    if origin_level is None:
        origin_level = RecordOriginLevel(kind.value)
    return schemas.TrackingRecordResponse(
        id=record.id,
        target_kind=kind,
        target_token=token,
        item_sequence=item_sequence,
        origin_level=origin_level,
        origin_shipment_id=origin_shipment_id,
        origin_label=origin_label,
        inherited=inherited,
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

    Called whenever the quantity of a Contribution that already has a tracking
    group changes (a no-op when it has none). Sequence numbers are printed on
    physical labels, so a live unit's token is never reissued:

    - **Growing** only appends the new trailing sequences. Units 1..n keep the
      tokens they were printed with, so a correction from 283 to 300 leaves
      283 labels valid and needs paper only for 284..300.
    - **Shrinking** retires the surplus trailing items (``active = False``).
      Their tokens stop resolving (``/track/{token}`` 404s) and they drop out
      of the QR bundle and every timeline, but the rows — and any scan history
      hanging off them — survive, per the soft-delete rule.
    - **Growing again after a shrink** mints *brand-new* rows with *brand-new*
      tokens for those sequences. The retired ones stay dead: whoever holds a
      label printed before the shrink is holding a unit that never arrived, so
      it must not come back to life pointing at a different physical piece.

    Staged only (no commit); the caller owns the transaction.
    """
    group = _group_for_contribution(db, contribution.id)
    if group is None:
        return

    target = min(contribution.quantity, MAX_TRACKED_UNITS)
    live = (
        db.query(models.TrackingItem)
        .filter(
            models.TrackingItem.group_id == group.id,
            models.TrackingItem.active.is_(True),
        )
        .all()
    )

    retired = False
    for item in live:
        if item.sequence > target:
            item.active = False
            retired = True
    # Flush the retirements before inserting, so a sequence being re-created
    # never collides with the row it replaces under the partial unique index
    # (``tracking_item_group_sequence_active``); statement order within a
    # single flush is not ours to choose.
    if retired:
        db.flush()

    existing = {item.sequence for item in live if item.sequence <= target}
    for sequence in range(1, target + 1):
        if sequence not in existing:
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
def _fetch_records(db: Session, conditions: list[Any]) -> list[models.TrackingRecord]:
    """All live records matching any of the target conditions, newest first."""
    return (
        db.query(models.TrackingRecord)
        .filter(
            models.TrackingRecord.active.is_(True),
            or_(*conditions),
        )
        .order_by(models.TrackingRecord.created_at.desc())
        .all()
    )


def _render_timeline(
    db: Session,
    record_rows: list[models.TrackingRecord],
    *,
    viewer: User | None,
    maker_id: UUID,
    group: models.TrackingGroup | None,
    token_by_item: dict[UUID, str],
    seq_by_item: dict[UUID, int],
    boxes: dict[UUID, _BoxFacts],
    own_level: RecordOriginLevel,
    own_item_id: UUID | None = None,
) -> list[schemas.TrackingRecordResponse]:
    """Turn mixed-level records into one timeline, flagging inherited entries.

    ``own_level`` is where the reader is standing; anything posted above it is
    marked ``inherited`` so the UI can badge it. Each entry keeps its own
    permalink target, so clicking a box update goes to the box.
    """
    records: list[schemas.TrackingRecordResponse] = []
    for record in record_rows:
        if record.shipment_id is not None:
            facts = boxes.get(record.shipment_id)
            if facts is None:  # pragma: no cover - ancestors were just loaded
                continue
            records.append(
                build_record_response(
                    db,
                    record,
                    kind=TrackingTargetKind.SHIPMENT,
                    token=facts.token,
                    viewer=viewer,
                    maker_id=maker_id,
                    origin_level=RecordOriginLevel.SHIPMENT,
                    origin_shipment_id=record.shipment_id,
                    origin_label=facts.label,
                    inherited=own_level is not RecordOriginLevel.SHIPMENT,
                )
            )
        elif record.tracking_group_id is not None:
            assert group is not None
            records.append(
                build_record_response(
                    db,
                    record,
                    kind=TrackingTargetKind.GROUP,
                    token=group.tracking_token,
                    viewer=viewer,
                    maker_id=maker_id,
                    origin_level=RecordOriginLevel.GROUP,
                    inherited=own_level is RecordOriginLevel.ITEM,
                )
            )
        else:
            item_id = record.tracking_item_id
            assert item_id is not None
            records.append(
                build_record_response(
                    db,
                    record,
                    kind=TrackingTargetKind.ITEM,
                    token=token_by_item[item_id],
                    viewer=viewer,
                    maker_id=maker_id,
                    item_sequence=seq_by_item[item_id],
                    origin_level=RecordOriginLevel.ITEM,
                    # An item entry is only "inherited" when read from a level
                    # that does not own it, which never happens: units are the
                    # bottom, and a group folds them in as its own children.
                    inherited=own_item_id is not None and item_id != own_item_id,
                )
            )
    return records


def _group_timeline(
    db: Session,
    group: models.TrackingGroup,
    viewer: User | None,
    maker_id: UUID,
    include_item_updates: bool,
    include_inherited: bool = True,
) -> list[schemas.TrackingRecordResponse]:
    """Build a package token's timeline.

    Three levels can land here. The package's own updates always; its units'
    updates when ``include_item_updates`` (they roll **up**, as they always
    have); and the updates of every box enclosing it when ``include_inherited``
    — those roll **down**, which is the point of taping a QR to a box.
    """
    token_by_item: dict[UUID, str] = {}
    seq_by_item: dict[UUID, int] = {}
    conditions: list[Any] = [models.TrackingRecord.tracking_group_id == group.id]

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

    boxes: dict[UUID, _BoxFacts] = {}
    if include_inherited:
        ancestors = _ancestor_shipment_ids(db, group_id=group.id)
        if ancestors:
            conditions.append(models.TrackingRecord.shipment_id.in_(ancestors))
            boxes = _box_facts(db, ancestors)

    return _render_timeline(
        db,
        _fetch_records(db, conditions),
        viewer=viewer,
        maker_id=maker_id,
        group=group,
        token_by_item=token_by_item,
        seq_by_item=seq_by_item,
        boxes=boxes,
        own_level=RecordOriginLevel.GROUP,
    )


def _item_timeline(
    db: Session,
    group: models.TrackingGroup,
    item: models.TrackingItem,
    viewer: User | None,
    maker_id: UUID,
    include_inherited: bool,
) -> list[schemas.TrackingRecordResponse]:
    """Build one unit's timeline, inheriting everything above it.

    A unit page shows its own updates, its package's, and every enclosing
    box's. "Left Caracas on the 3rd" is true of every piece in that box, so it
    has to read on the piece's own page — otherwise the box QR would be the
    only place the news ever appears, and the whole point of the waterfall is
    that one update reaches every unit inside.

    ``include_inherited=False`` narrows back to this unit's own updates, which
    is what the scope toggle offers.
    """
    conditions: list[Any] = [models.TrackingRecord.tracking_item_id == item.id]
    boxes: dict[UUID, _BoxFacts] = {}
    if include_inherited:
        conditions.append(models.TrackingRecord.tracking_group_id == group.id)
        ancestors = _ancestor_shipment_ids(db, group_id=group.id)
        if ancestors:
            conditions.append(models.TrackingRecord.shipment_id.in_(ancestors))
            boxes = _box_facts(db, ancestors)

    return _render_timeline(
        db,
        _fetch_records(db, conditions),
        viewer=viewer,
        maker_id=maker_id,
        group=group,
        token_by_item={item.id: item.tracking_token},
        seq_by_item={item.id: item.sequence},
        boxes=boxes,
        own_level=RecordOriginLevel.ITEM,
        own_item_id=item.id,
    )


def _shipment_timeline(
    db: Session,
    shipment: "Shipment",
    viewer: User | None,
    include_inherited: bool,
) -> list[schemas.TrackingRecordResponse]:
    """Build a box token's timeline — box-level updates only.

    Deliberately **never** folds in the packages inside. A box is public while
    the packages it carries may be ``private``; rolling their updates up here
    would publish them to anyone who photographed the box. The waterfall runs
    one way only (FR-146).
    """
    ancestors = _ancestor_shipment_ids(db, shipment_id=shipment.id)
    ids = [shipment.id, *ancestors] if include_inherited else [shipment.id]
    boxes = _box_facts(db, ids)
    return _render_timeline(
        db,
        _fetch_records(db, [models.TrackingRecord.shipment_id.in_(ids)]),
        viewer=viewer,
        # A box has no single maker, so nobody gets maker-level tag-edit
        # rights from it; authors and maintainers still do.
        maker_id=UUID(int=0),
        group=None,
        token_by_item={},
        seq_by_item={},
        boxes=boxes,
        own_level=RecordOriginLevel.SHIPMENT,
    )


def get_public_view(
    db: Session,
    token: str,
    viewer: User | None,
    include_item_updates: bool = True,
    include_inherited: bool = True,
) -> schemas.PublicTrackingResponse:
    """Resolve any of the three token kinds and return its gated timeline.

    On a **package** token, ``include_item_updates`` (default) folds every
    per-unit update in as well; set it False for package-level updates only.
    ``include_inherited`` (default) folds in the updates of every box enclosing
    what was scanned — the downward waterfall — and, on a unit token, its
    package's updates too. Both are what the scope toggle drives.
    """
    resolved = _resolve_token(db, token)
    if resolved.kind is TrackingTargetKind.SHIPMENT:
        assert resolved.shipment is not None
        return _public_shipment_view(db, resolved.shipment, viewer, include_inherited)

    group, item = resolved.group, resolved.item
    assert group is not None
    if not _can_view(db, group, viewer):
        raise TrackingForbiddenExceptionError
    contribution = _get_contribution(db, group.contribution_id)
    resource_name, resource_image_url, label_url, _ = _resource_context(
        db, contribution
    )
    can_manage = viewer is not None and has_global_override(viewer)

    if resolved.kind is TrackingTargetKind.ITEM and item is not None:
        records = _item_timeline(
            db, group, item, viewer, contribution.maker_id, include_inherited
        )
    else:
        records = _group_timeline(
            db,
            group,
            viewer,
            contribution.maker_id,
            include_item_updates,
            include_inherited,
        )

    from app.contributions.service import can_confirm_received

    return schemas.PublicTrackingResponse(
        target_kind=resolved.kind,
        tracking_token=token,
        group_id=group.id,
        visibility=group.visibility,
        resource_name=resource_name,
        resource_image_url=resource_image_url,
        contribution_status=str(contribution.status),
        quantity=contribution.quantity,
        tracked_units=count_tracked_units(db, group.id),
        item_sequence=item.sequence if item is not None else None,
        records=records,
        can_contribute=True,
        can_mark_received=can_confirm_received(db, contribution, viewer),
        can_manage=can_manage,
        resource_has_label=can_manage and label_url is not None,
        watching=_is_watching_group(db, group.id, viewer),
        packing=_packing_context(db, viewer, group_id=group.id),
    )


def _packing_context(
    db: Session,
    viewer: User | None,
    *,
    group_id: UUID | None = None,
    shipment_id: UUID | None = None,
) -> schemas.PackingContext | None:
    """Offer the scanner a box to drop this into (``None`` for non-members).

    This is the packing-table workflow the box QRs exist for: a center member
    scans whatever is in their hand, lands here, and files it into a shipment
    without navigating anywhere. Guests and makers see nothing — they staff no
    center, so there is no box for them to file into.
    """
    from app.shipments import service as shipments_service

    if viewer is None:
        return None

    # Nesting a box into itself, or into something it already contains, is a
    # cycle; drop those from the picker rather than letting the write fail.
    exclude: set[UUID] = set()
    if shipment_id is not None:
        exclude = set(shipments_service.descendant_shipment_ids(db, shipment_id))

    options = shipments_service.open_boxes_for(db, viewer, exclude_ids=exclude)
    holder = shipments_service.holder_of(
        db, tracking_group_id=group_id, child_shipment_id=shipment_id
    )
    if not options and holder is None:
        return None

    return schemas.PackingContext(
        current_shipment_id=holder[0] if holder else None,
        current_shipment_label=holder[1] if holder else None,
        current_shipment_token=holder[2] if holder else None,
        options=[
            schemas.PackingOption(
                shipment_id=box.shipment_id,
                collection_center_id=box.collection_center_id,
                label=box.label,
            )
            for box in options
        ],
    )


def _public_shipment_view(
    db: Session,
    shipment: "Shipment",
    viewer: User | None,
    include_inherited: bool,
) -> schemas.PublicTrackingResponse:
    """Public payload for a scanned box.

    Boxes carry no visibility tier of their own: holding the token is enough to
    read one, exactly as for a ``public`` package (FR-130). What the box is
    *carrying* is gated separately, in the manifest — see
    ``shipments.service.list_contents``.
    """
    from app.shipments import service as shipments_service
    from app.shipments.constants import ARRIVABLE_STATUSES

    can_manage = shipments_service.can_manage_shipment(db, shipment, viewer)
    contents = shipments_service.list_contents(
        db, shipment.collection_center_id, shipment.id, viewer
    )
    route = [
        schemas.ShipmentRouteHop(
            shipment_id=box_id,
            tracking_token=facts.token,
            label=facts.label,
        )
        for box_id, facts in _box_facts(
            db, _ancestor_shipment_ids(db, shipment_id=shipment.id)
        ).items()
    ]
    summary = schemas.ShipmentTrackingSummary(
        id=shipment.id,
        status=shipment.status.value,
        shipment_date=shipment.shipment_date,
        destination=shipments_service.destination_label(db, shipment),
        origin_center_id=shipment.collection_center_id,
        destination_center_id=shipment.destination_collection_center_id,
        dispatched_at=shipment.dispatched_at,
        arrived_at=shipment.arrived_at,
        package_count=contents.package_count,
        child_count=contents.child_count,
        units_total=contents.units_total,
        hidden_count=contents.hidden_count,
        route=route,
        # Already limited to box custodians by ``list_contents`` (FR-146).
        entries=contents.entries,
        can_manage_contents=can_manage,
        can_mark_arrived=can_manage and shipment.status in ARRIVABLE_STATUSES,
    )
    return schemas.PublicTrackingResponse(
        target_kind=TrackingTargetKind.SHIPMENT,
        tracking_token=shipment.tracking_token,
        group_id=None,
        visibility=None,
        resource_name=None,
        resource_image_url=None,
        contribution_status=None,
        quantity=None,
        tracked_units=0,
        item_sequence=None,
        records=_shipment_timeline(db, shipment, viewer, include_inherited),
        can_contribute=True,
        can_mark_received=False,
        can_manage=can_manage,
        resource_has_label=False,
        watching=False,
        shipment=summary,
        packing=_packing_context(db, viewer, shipment_id=shipment.id),
    )


def count_tracked_units(db: Session, group_id: UUID) -> int:
    """How many units of a group currently carry a live QR."""
    return (
        db.query(func.count(models.TrackingItem.id))
        .filter(
            models.TrackingItem.group_id == group_id,
            models.TrackingItem.active.is_(True),
        )
        .scalar()
        or 0
    )


def adjust_quantity_by_token(
    db: Session, token: str, quantity: int, actor: User
) -> str:
    """Correct the scanned Contribution's unit count (maintainer/admin).

    Exposed on the scan surface because that is where the discrepancy shows
    up: the center opens the package, counts 300 pieces against the maker's
    283, and fixes it on the page it already has open. Authorization is the
    Contribution's own maintainer/admin override and is deliberately
    **independent of the tracking visibility** — holding the token is not a
    licence to rewrite the commitment.

    Returns the token to render afterwards: the caller's own, unless a shrink
    just retired the very unit they were standing on, in which case its group
    token — the write succeeded, so answering with that unit's 404 would read
    as a failure.
    """
    from app.contributions.service import adjust_quantity
    from app.shipments.exceptions import ShipmentTokenNotSupportedExceptionError

    resolved = _resolve_token(db, token)
    if resolved.kind is TrackingTargetKind.SHIPMENT:
        # A box has no unit count of its own — only the packages inside it do,
        # each with its own. Correcting one means scanning that package.
        raise ShipmentTokenNotSupportedExceptionError("quantity correction")
    group, item = resolved.group, resolved.item
    assert group is not None
    adjust_quantity(db, group.contribution_id, quantity, actor)
    if item is not None and item.sequence > min(quantity, MAX_TRACKED_UNITS):
        return group.tracking_token
    return token


def confirm_received_by_token(db: Session, token: str, actor: User) -> None:
    """Log the arrival of whatever was scanned (FR-056, FR-143).

    On a package or unit token the receipt is a Contribution-level fact, so
    either marks the whole contribution received. Authorization is the
    Contribution's own (effective member of its drop-off center) and is
    deliberately **independent of the tracking visibility**: a center member
    who scans a private package can still log the arrival, and a mere token
    holder still cannot.

    On a **box** token it means the box arrived, which bulk-receives every
    Contribution inside it. That is the same physical act — "this reached us" —
    performed on the container instead of one package, so it belongs on the
    same button rather than a second endpoint the dock staff would have to
    know about.
    """
    from app.contributions.service import confirm_received

    resolved = _resolve_token(db, token)
    if resolved.kind is TrackingTargetKind.SHIPMENT:
        from app.shipments import service as shipments_service

        shipment = resolved.shipment
        assert shipment is not None
        shipments_service.mark_arrived(
            db, shipment.collection_center_id, shipment.id, actor
        )
        return
    assert resolved.group is not None
    confirm_received(db, resolved.group.contribution_id, actor)


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
    resolved = _resolve_token(db, token)
    kind, group, item, shipment = resolved
    if group is not None and not _can_view(db, group, viewer):
        raise TrackingForbiddenExceptionError
    # A box carries no maker of its own; nobody gains maker-level tag rights
    # from posting on one.
    maker_id = (
        _get_contribution(db, group.contribution_id).maker_id
        if group is not None
        else UUID(int=0)
    )

    record = models.TrackingRecord(
        tracking_group_id=(
            group.id if group is not None and kind is TrackingTargetKind.GROUP else None
        ),
        tracking_item_id=item.id if item is not None else None,
        shipment_id=shipment.id if shipment is not None else None,
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
    if group is not None:
        _notify_group_watchers(db, group.id, actor_id, record.id)
    else:
        assert shipment is not None
        from app.shipments import service as shipments_service

        shipments_service.notify_box_audience(
            db, shipment, actor_id, record.id, payload.description
        )
    db.commit()
    db.refresh(record)
    return (
        kind,
        maker_id,
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
) -> tuple[models.TrackingGroup, "Contribution"] | None:
    """The package and Contribution behind a record, or ``None`` for a box.

    A box update belongs to a shipment, not to any one Contribution, so there
    is no maker to grant edit rights. Callers must branch on ``None`` — the
    previous version asserted its way to a 500 the moment a box record existed.
    """
    if record.shipment_id is not None:
        return None
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


def _box_for_record(db: Session, record: models.TrackingRecord) -> "Shipment":
    from app.shipments.models import Shipment as ShipmentModel

    box = db.get(ShipmentModel, record.shipment_id)
    if box is None:  # pragma: no cover - shipments are soft-deleted, never removed
        raise RecordNotFoundExceptionError(record.id)
    return box


def edit_record_tags(
    db: Session,
    record_id: UUID,
    actor: User,
    tags: list[str],
) -> tuple[models.TrackingRecord, TrackingTargetKind, str, UUID, int | None]:
    """Replace a record's tags (author / contribution owner / maintainer).

    On a **box** update there is no maker, so the owner tier becomes the staff
    holding the box — its origin or destination center — which is the same set
    that could have posted the update in the first place.
    """
    record = _get_record(db, record_id)
    resolved = _contribution_for_record(db, record)

    if resolved is None:
        from app.shipments import service as shipments_service

        box = _box_for_record(db, record)
        may_edit = record.author_user_id == actor.id or (
            shipments_service.can_manage_shipment(db, box, actor)
        )
        if not may_edit:
            raise RecordEditForbiddenExceptionError
        record.tags = tags
        db.commit()
        db.refresh(record)
        return (
            record,
            TrackingTargetKind.SHIPMENT,
            box.tracking_token,
            UUID(int=0),
            None,
        )

    group, contribution = resolved
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


def select_bundle_items(
    items: list[tuple[int, str]], seq_from: int | None, seq_to: int | None
) -> list[tuple[int, str]]:
    """Narrow a bundle's per-unit QRs to a printable sequence window.

    Reprinting a window is the normal case once a count is corrected: units
    1..283 already carry paper labels, only 284..300 need any. An omitted bound
    is open-ended; an empty window raises rather than rendering a blank sheet,
    which is otherwise indistinguishable from a successful print.
    """
    if seq_from is None and seq_to is None:
        return items
    low = seq_from if seq_from is not None else 1
    high = seq_to if seq_to is not None else max((s for s, _ in items), default=0)
    selected = [(s, t) for s, t in items if low <= s <= high]
    if not selected:
        raise InvalidUnitRangeExceptionError(low, high)
    return selected


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


def group_caption(total_units: int) -> str:
    """Caption for the group QR: how many units the package holds."""
    unit_word = "item" if total_units == 1 else "items"
    return f"{QR_GROUP_CAPTION} · {total_units} {unit_word}"


def item_caption(sequence: int, total_units: int) -> str:
    """Caption for one unit's QR: which unit it is, out of how many.

    Printed as ``#3/20`` so a piece that gets separated from its package is
    still placeable — the label carries the whole group's size, not just the
    unit's own number.
    """
    return f"#{sequence}/{total_units}"


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
