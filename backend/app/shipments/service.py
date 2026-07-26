"""Shipment business logic: public reads, member-gated writes (FR-127..130).

Shipments belong to a Collection Center. Reads are public so the
community can see drop-off deadlines; writes require an effective member
of the center (owner, contributor, owning-org member) or a maintainer /
admin. Every mutation is mirrored into the public activity timeline.

A shipment is also the **box** that Contributions physically ride in, and
that other boxes nest inside (FR-138). This module therefore owns the
containment graph: who is packed into what, how deep, and — because the
graph is a forest, one active parent per thing — how to walk it in either
direction. The tracking domain consumes those walks to waterfall a box
update down onto every package and unit inside it.
"""

from datetime import UTC, datetime
from typing import NamedTuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.activity import service as activity_service
from app.activity.constants import ActivityAction, EntityType
from app.collection_centers import service as cc_service
from app.collection_centers.exceptions import NotEffectiveMemberExceptionError
from app.tracking.tokens import new_token
from app.users.models import User

from . import models, schemas
from .constants import (
    MAX_SHIPMENT_DEPTH,
    PACKABLE_STATUSES,
    SHIPMENT_TRANSITIONS,
    ShipmentStatus,
)
from .exceptions import (
    AlreadyPackedExceptionError,
    InvalidShipmentTransitionExceptionError,
    ShipmentContentNotFoundExceptionError,
    ShipmentCycleExceptionError,
    ShipmentLockedExceptionError,
    ShipmentNotFoundExceptionError,
    ShipmentTooDeepExceptionError,
)


def _assert_can_manage(db: Session, collection_center_id: UUID, actor: User) -> None:
    """Require the actor to be an effective member of the center (FR-129).

    ``is_effective_member`` already folds in the maintainer/admin global
    override, so this one call covers both.
    """
    cc = cc_service.get_or_raise(db, collection_center_id)
    if not cc_service.is_effective_member(db, cc, actor):
        raise NotEffectiveMemberExceptionError


def can_manage_shipment(
    db: Session, shipment: models.Shipment, actor: User | None
) -> bool:
    """Whether ``actor`` may pack, unpack, and move this box (FR-144).

    Custody, not roster, is what authorizes: the actor must staff the box's
    **origin** center or its **destination** center. A relay hop is staffed by
    neither the maker's original drop-off center nor, necessarily, the final
    one, so authorizing per contained Contribution would make relay handling
    impossible. ``is_effective_member`` already grants maintainers and admins.
    """
    if actor is None:
        return False
    from app.collection_centers.models import CollectionCenter

    center_ids = [shipment.collection_center_id]
    if shipment.destination_collection_center_id is not None:
        center_ids.append(shipment.destination_collection_center_id)
    for center_id in center_ids:
        # Loaded directly rather than through ``cc_service.get_or_raise``: an
        # archived center still has staff, and they must not lose the ability
        # to sign for a box that is already on the road to them.
        cc = db.get(CollectionCenter, center_id)
        if cc is not None and cc_service.is_effective_member(db, cc, actor):
            return True
    return False


def _assert_can_manage_shipment(
    db: Session, shipment: models.Shipment, actor: User
) -> None:
    if not can_manage_shipment(db, shipment, actor):
        raise NotEffectiveMemberExceptionError


# --------------------------------------------------------------------------- #
# Containment graph
# --------------------------------------------------------------------------- #
# The two partial unique indexes on ``shipment_contents`` mean a package — or a
# box — has **at most one** active parent, so containment is a forest rather
# than a general graph. That is what lets these walks be simple loops instead of
# recursive CTEs: each hop is one indexed lookup, the common case (an unpacked
# package) costs a single query, and real relay chains are two or three deep.
# Every walk still carries ``MAX_SHIPMENT_DEPTH`` and a ``seen`` set, so a
# corrupted row can slow a request down but can never hang it.


def _active_parent_row(
    db: Session,
    *,
    tracking_group_id: UUID | None = None,
    child_shipment_id: UUID | None = None,
) -> models.ShipmentContent | None:
    """The manifest line currently holding this package or box, if any."""
    query = db.query(models.ShipmentContent).filter(
        models.ShipmentContent.active.is_(True)
    )
    if tracking_group_id is not None:
        query = query.filter(
            models.ShipmentContent.tracking_group_id == tracking_group_id
        )
    else:
        query = query.filter(
            models.ShipmentContent.child_shipment_id == child_shipment_id
        )
    return query.first()


def ancestor_shipment_ids(
    db: Session,
    *,
    tracking_group_id: UUID | None = None,
    shipment_id: UUID | None = None,
) -> list[UUID]:
    """Boxes enclosing this package or box, innermost first (FR-145).

    Empty when the thing is not packed into anything — the common case, and
    the reason this costs one query for most ``/track`` renders.
    """
    row = _active_parent_row(
        db, tracking_group_id=tracking_group_id, child_shipment_id=shipment_id
    )
    chain: list[UUID] = []
    seen: set[UUID] = set()
    while row is not None and len(chain) < MAX_SHIPMENT_DEPTH:
        parent_id = row.shipment_id
        if parent_id in seen:
            break
        seen.add(parent_id)
        chain.append(parent_id)
        row = _active_parent_row(db, child_shipment_id=parent_id)
    return chain


def descendant_shipment_ids(db: Session, shipment_id: UUID) -> list[UUID]:
    """This box plus every box nested inside it, breadth-first (root first)."""
    found = [shipment_id]
    seen = {shipment_id}
    frontier = [shipment_id]
    for _ in range(MAX_SHIPMENT_DEPTH):
        if not frontier:
            break
        rows = (
            db.query(models.ShipmentContent.child_shipment_id)
            .filter(
                models.ShipmentContent.shipment_id.in_(frontier),
                models.ShipmentContent.child_shipment_id.isnot(None),
                models.ShipmentContent.active.is_(True),
            )
            .all()
        )
        frontier = []
        for (child_id,) in rows:
            if child_id is not None and child_id not in seen:
                seen.add(child_id)
                found.append(child_id)
                frontier.append(child_id)
    return found


def _subtree_height(db: Session, shipment_id: UUID) -> int:
    """How many levels of boxes hang below this one (0 when it holds none)."""
    frontier = [shipment_id]
    seen = {shipment_id}
    height = 0
    for _ in range(MAX_SHIPMENT_DEPTH):
        rows = (
            db.query(models.ShipmentContent.child_shipment_id)
            .filter(
                models.ShipmentContent.shipment_id.in_(frontier),
                models.ShipmentContent.child_shipment_id.isnot(None),
                models.ShipmentContent.active.is_(True),
            )
            .all()
        )
        nxt = [c for (c,) in rows if c is not None and c not in seen]
        if not nxt:
            break
        seen.update(nxt)
        frontier = nxt
        height += 1
    return height


def contained_group_ids(db: Session, shipment_id: UUID) -> list[UUID]:
    """Every packed tracking group inside this box, at any nesting depth."""
    boxes = descendant_shipment_ids(db, shipment_id)
    rows = (
        db.query(models.ShipmentContent.tracking_group_id)
        .filter(
            models.ShipmentContent.shipment_id.in_(boxes),
            models.ShipmentContent.tracking_group_id.isnot(None),
            models.ShipmentContent.active.is_(True),
        )
        .all()
    )
    return [group_id for (group_id,) in rows if group_id is not None]


def get_or_raise(
    db: Session, collection_center_id: UUID, shipment_id: UUID
) -> models.Shipment:
    """Return an active shipment scoped to its center, or raise ``NotFound``."""
    shipment = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.id == shipment_id,
            models.Shipment.collection_center_id == collection_center_id,
            models.Shipment.active.is_(True),
        )
        .first()
    )
    if shipment is None:
        raise ShipmentNotFoundExceptionError(shipment_id)
    return shipment


def list_shipments(db: Session, collection_center_id: UUID) -> list[models.Shipment]:
    """List a center's active shipments, soonest date first (public, FR-130)."""
    cc_service.get_or_raise(db, collection_center_id)
    return (
        db.query(models.Shipment)
        .filter(
            models.Shipment.collection_center_id == collection_center_id,
            models.Shipment.active.is_(True),
        )
        .order_by(models.Shipment.shipment_date.asc())
        .all()
    )


def list_my_shipments(db: Session, actor: User) -> list[schemas.MyShipmentResponse]:
    """Every shipment at a center the caller staffs (FR-129).

    The centers tab is the public directory; this is the working queue. Scoped
    by **roster**, not by who pressed create, so a contributor helping run a
    center sees the same boxes its owner does and a handover never depends on
    which of them started the shipment.
    """
    from app.collection_centers.models import CollectionCenter

    centers = cc_service.list_my_centers(db, actor)
    if not centers:
        return []
    names = {center.id: center.name for center in centers}

    shipments = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.collection_center_id.in_(list(names)),
            models.Shipment.active.is_(True),
        )
        .order_by(models.Shipment.shipment_date.desc())
        .all()
    )
    # Destination names for relay legs, which usually point at centers the
    # caller does *not* staff, so they are not in ``names``.
    destination_ids = {
        s.destination_collection_center_id
        for s in shipments
        if s.destination_collection_center_id is not None
    }
    destinations: dict[UUID, str] = {}
    if destination_ids:
        destinations = {
            row.id: row.name
            for row in db.query(CollectionCenter)
            .filter(CollectionCenter.id.in_(list(destination_ids)))
            .all()
        }

    return [
        schemas.MyShipmentResponse(
            **schemas.ShipmentResponse.model_validate(shipment).model_dump(),
            collection_center_name=names[shipment.collection_center_id],
            destination_collection_center_name=(
                destinations.get(shipment.destination_collection_center_id)
                if shipment.destination_collection_center_id is not None
                else None
            ),
            # One containment walk per shipment. Fine for a personal list of
            # tens of boxes; revisit if a center ever runs hundreds at once.
            package_count=len(contained_group_ids(db, shipment.id)),
        )
        for shipment in shipments
    ]


def create_shipment(
    db: Session,
    collection_center_id: UUID,
    payload: schemas.ShipmentCreate,
    actor: User,
) -> models.Shipment:
    """Create a shipment (effective member or maintainer/admin, FR-129)."""
    _assert_can_manage(db, collection_center_id, actor)
    shipment = models.Shipment(
        collection_center_id=collection_center_id,
        shipment_date=payload.shipment_date,
        status=payload.status,
        destination=payload.destination,
        destination_collection_center_id=payload.destination_collection_center_id,
        description=payload.description,
        # Every box is scannable from birth (FR-137). Minting here rather than
        # on a separate "generate QR" call means nothing downstream — the label
        # printer, the manifest, the scan surface — has to cope with a box that
        # has no token yet.
        tracking_token=new_token(),
        created_by_id=actor.id,
    )
    db.add(shipment)
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor.id,
        action=ActivityAction.CREATED,
        changes={
            "shipment_date": payload.shipment_date.isoformat(),
            "status": payload.status.value,
        },
    )
    db.commit()
    db.refresh(shipment)
    return shipment


def update_shipment(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    payload: schemas.ShipmentUpdate,
    actor: User,
) -> models.Shipment:
    """Edit a shipment, recording status transitions distinctly (FR-129)."""
    _assert_can_manage(db, collection_center_id, actor)
    shipment = get_or_raise(db, collection_center_id, shipment_id)

    fields = payload.model_dump(exclude_unset=True)
    old_status = shipment.status
    new_status: ShipmentStatus | None = fields.get("status")
    if new_status is not None:
        _assert_transition(old_status, new_status)
    for field, value in fields.items():
        setattr(shipment, field, value)
    # A cancelled box must not keep its packages hostage: the single-active-
    # parent index would otherwise mark them packed into something that is
    # never leaving. Arriving does the opposite — the contents stay listed,
    # because the manifest is what the receiving team checks against.
    if new_status is ShipmentStatus.CANCELLED:
        release_contents(db, shipment, actor)
    db.flush()

    if new_status is not None and new_status != old_status:
        activity_service.record(
            db,
            entity_type=EntityType.SHIPMENT,
            entity_id=shipment.id,
            actor_user_id=actor.id,
            action=ActivityAction.STATUS_CHANGED,
            changes={"status": {"from": old_status.value, "to": new_status.value}},
        )
    else:
        activity_service.record(
            db,
            entity_type=EntityType.SHIPMENT,
            entity_id=shipment.id,
            actor_user_id=actor.id,
            action=ActivityAction.UPDATED,
            changes={k: str(v) for k, v in fields.items()},
        )

    db.commit()
    db.refresh(shipment)
    return shipment


class ArrivalResult(NamedTuple):
    """What a box arrival did to the Contributions inside it."""

    received: int
    skipped_already: int
    skipped_no_center: int
    packages_total: int


def _assert_transition(
    current: ShipmentStatus, target: ShipmentStatus, *, allow_noop: bool = True
) -> None:
    """Guard the lifecycle map (FR-141).

    ``allow_noop`` distinguishes the two callers. A ``PATCH`` that re-sends the
    status it already has is a harmless idempotent edit, so it passes. The
    lifecycle endpoints set it False: signing for the same box twice is a
    mistake worth surfacing, not a no-op — and ``/receive-contents`` exists for
    the genuinely re-runnable case.
    """
    if target is current:
        if allow_noop:
            return
        raise InvalidShipmentTransitionExceptionError(current, target)
    if target not in SHIPMENT_TRANSITIONS[current]:
        raise InvalidShipmentTransitionExceptionError(current, target)


def _receive_contained(
    db: Session, shipment: models.Shipment, actor: User
) -> ArrivalResult:
    """Confirm every pre-receipt Contribution inside the box (FR-143).

    Recursive: a relay box holds other boxes, and the packages two levels down
    arrived just as physically as the ones on top. Staged only — the caller
    owns the transaction, so a box either lands whole or not at all.

    Skips rather than fails on the two cases that are not errors: a
    Contribution already ``received``/``released`` (the common case at a relay
    hop, where the origin center confirmed receipt weeks ago), and one with no
    drop-off center. One odd package must not roll back the other thirty-seven.

    Returns the counts; the arrival notification goes to everyone with a
    package in the box, not only whoever this pass happened to receive.
    """
    from app.contributions.constants import RECEIVABLE_STATUSES
    from app.contributions.models import Contribution
    from app.contributions.service import apply_receipt
    from app.tracking.models import TrackingGroup

    group_ids = contained_group_ids(db, shipment.id)
    if not group_ids:
        return ArrivalResult(0, 0, 0, 0)

    contributions = (
        db.query(Contribution)
        .join(TrackingGroup, TrackingGroup.contribution_id == Contribution.id)
        .filter(TrackingGroup.id.in_(group_ids))
        .all()
    )
    received = skipped_already = skipped_no_center = 0
    for contribution in contributions:
        if contribution.status not in RECEIVABLE_STATUSES:
            skipped_already += 1
            continue
        if contribution.collection_center_id is None:
            skipped_no_center += 1
            continue
        # ``collection_center_id`` is deliberately left alone: it records where
        # the maker actually dropped off, which is not where this box landed.
        apply_receipt(db, contribution, actor, notify=False)
        received += 1
    db.flush()
    return ArrivalResult(
        received=received,
        skipped_already=skipped_already,
        skipped_no_center=skipped_no_center,
        packages_total=len(contributions),
    )


def _box_update(
    db: Session, shipment: models.Shipment, actor: User, description: str
) -> UUID:
    """Post one update on the box's own timeline (flush only).

    This single row is what the waterfall turns into news on every package and
    unit inside the box — one write, N timelines updated (FR-145).
    """
    from app.tracking.models import TrackingRecord

    record = TrackingRecord(
        shipment_id=shipment.id,
        author_user_id=actor.id,
        description=description,
        tags=[shipment.status.value],
    )
    db.add(record)
    db.flush()
    return record.id


def contained_maker_ids(db: Session, shipment_id: UUID) -> set[UUID]:
    """The makers of every package inside this box, at any nesting depth."""
    from app.contributions.models import Contribution
    from app.tracking.models import TrackingGroup

    group_ids = contained_group_ids(db, shipment_id)
    if not group_ids:
        return set()
    return {
        maker_id
        for (maker_id,) in db.query(Contribution.maker_id)
        .join(TrackingGroup, TrackingGroup.contribution_id == Contribution.id)
        .filter(TrackingGroup.id.in_(group_ids))
        .all()
    }


def notify_box_audience(
    db: Session,
    shipment: models.Shipment,
    actor_id: UUID,
    record_id: UUID,
    description: str,
) -> None:
    """Tell each person with something in this box, once (FR-148).

    Recipients are the makers of every package inside, at any depth, collected
    into a **set** before delivery. A maker with three packages in the same box
    hears about it once, not three times — and nobody hears once per printed
    unit. Everyone inside is told, not only whoever a bulk receipt happened to
    touch: "the box landed" matters just as much to a maker whose package was
    receipted upstream weeks ago.

    Staged only; the caller owns the transaction.
    """
    from app.activity.constants import EntityType
    from app.notifications import service as notifications_service
    from app.notifications.constants import TRACKING_UPDATE_EVENT, NotificationReason

    maker_ids = contained_maker_ids(db, shipment.id)
    if not maker_ids:
        return
    notifications_service.fan_out_to_users(
        db,
        recipient_ids=maker_ids,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor_id,
        event=TRACKING_UPDATE_EVENT,
        reason=NotificationReason.WATCH,
        anchor=f"record-{record_id}",
        extra_payload={"note": description},
    )


def _advance(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    target: ShipmentStatus,
    actor: User,
) -> models.Shipment:
    """Shared body for the dispatch/arrive/close lifecycle endpoints."""
    shipment = get_or_raise(db, collection_center_id, shipment_id)
    _assert_can_manage_shipment(db, shipment, actor)
    _assert_transition(shipment.status, target, allow_noop=False)
    previous = shipment.status
    shipment.status = target
    if target is ShipmentStatus.IN_TRANSIT:
        shipment.dispatched_at = datetime.now(UTC)
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor.id,
        action=ActivityAction.STATUS_CHANGED,
        changes={"status": {"from": previous.value, "to": target.value}},
    )
    return shipment


def dispatch(
    db: Session, collection_center_id: UUID, shipment_id: UUID, actor: User
) -> models.Shipment:
    """Send the box on its way, freezing its manifest (FR-141)."""
    shipment = _advance(
        db, collection_center_id, shipment_id, ShipmentStatus.IN_TRANSIT, actor
    )
    _box_update(db, shipment, actor, _dispatch_note(db, shipment))
    db.commit()
    db.refresh(shipment)
    return shipment


def mark_arrived(
    db: Session, collection_center_id: UUID, shipment_id: UUID, actor: User
) -> tuple[models.Shipment, ArrivalResult]:
    """Sign for the box and confirm everything inside it (FR-143).

    The one scan that clears a pallet: status, arrival stamps, every contained
    Contribution's receipt, one box-level update, and one notification per
    affected person — all in a single transaction.
    """
    shipment = _advance(
        db, collection_center_id, shipment_id, ShipmentStatus.ARRIVED, actor
    )
    shipment.arrived_at = datetime.now(UTC)
    shipment.arrived_by_id = actor.id
    result = _receive_contained(db, shipment, actor)
    note = _arrival_note(db, shipment, result)
    record_id = _box_update(db, shipment, actor, note)
    notify_box_audience(db, shipment, actor.id, record_id, note)
    db.commit()
    db.refresh(shipment)
    return shipment, result


def receive_contents(
    db: Session, collection_center_id: UUID, shipment_id: UUID, actor: User
) -> ArrivalResult:
    """Re-run the bulk receipt without touching the status (idempotent).

    ``/arrive`` can only fire once — a second call is a 409 — but the need
    recurs: a package turns up late and is added to a box already marked
    arrived, or a maker's receipt failed the first time round. This is the
    re-runnable twin. Receiving nothing is a success, not an error.
    """
    shipment = get_or_raise(db, collection_center_id, shipment_id)
    _assert_can_manage_shipment(db, shipment, actor)
    result = _receive_contained(db, shipment, actor)
    if result.received:
        note = _arrival_note(db, shipment, result)
        record_id = _box_update(db, shipment, actor, note)
        notify_box_audience(db, shipment, actor.id, record_id, note)
    db.commit()
    return result


def destination_label(db: Session, shipment: models.Shipment) -> str:
    """Human name for where a box is headed, for notes, captions and labels."""
    if shipment.destination_collection_center_id is not None:
        from app.collection_centers.models import CollectionCenter

        cc = db.get(CollectionCenter, shipment.destination_collection_center_id)
        if cc is not None:
            return cc.name
    return shipment.destination or "destino sin especificar"


class BoxLabelContext(NamedTuple):
    """Everything the box-label renderer needs. Presentation stays in ``qr``."""

    title: str
    subtitle: str
    lines: list[str]
    manifest_header: str
    manifest_rows: list[str]


def box_label_context(
    db: Session, collection_center_id: UUID, shipment_id: UUID, actor: User
) -> tuple[models.Shipment, BoxLabelContext]:
    """Build the label copy for a box (member-gated, FR-149).

    The manifest is rendered from the **full** contents, not the redacted
    view: only staff who already hold the box can reach this, and a checklist
    that hides half the box is worse than useless.
    """
    from app.collection_centers.models import CollectionCenter

    shipment = get_or_raise(db, collection_center_id, shipment_id)
    _assert_can_manage_shipment(db, shipment, actor)
    contents = list_contents(db, collection_center_id, shipment_id, actor)

    origin = db.get(CollectionCenter, shipment.collection_center_id)
    origin_name = origin.name if origin is not None else "origen desconocido"
    lines = [
        f"{contents.package_count} aportes · {contents.units_total} piezas",
    ]
    if contents.child_count:
        lines.append(f"Incluye {contents.child_count} caja(s) anidada(s)")

    rows: list[str] = []
    for entry in contents.entries:
        if entry.kind is schemas.ContentKind.BOX:
            rows.append(
                f"[caja] → {entry.child_destination or 'sin destino'} "
                f"· {entry.child_package_count or 0} aportes"
            )
        else:
            rows.append(
                f"{entry.quantity or '?'} x {entry.resource_name or '(reservado)'} "
                f"· {entry.maker_username or '—'}"
            )

    return shipment, BoxLabelContext(
        title=f"→ {destination_label(db, shipment)}",
        subtitle=f"Desde: {origin_name} · {shipment.shipment_date.isoformat()}",
        lines=lines,
        manifest_header=(f"Contenido de la caja → {destination_label(db, shipment)}"),
        manifest_rows=rows,
    )


def _dispatch_note(db: Session, shipment: models.Shipment) -> str:
    return f"Salió hacia {destination_label(db, shipment)}."


def _arrival_note(db: Session, shipment: models.Shipment, result: ArrivalResult) -> str:
    where = destination_label(db, shipment)
    if result.received:
        return f"Llegó a {where} · {result.received} aportes confirmados."
    return f"Llegó a {where}."


class _PackageFacts(NamedTuple):
    """Everything a manifest line needs about one packed Contribution."""

    resource_name: str
    quantity: int
    status: str
    maker: User
    tracking_token: str


def _package_facts(db: Session, group_ids: list[UUID]) -> dict[UUID, _PackageFacts]:
    """Batch-load the manifest facts for a set of tracking groups.

    One join instead of a query per line: a relay box can hold a hundred
    packages, and this runs on every scan of it.
    """
    if not group_ids:
        return {}
    from app.contributions.models import Contribution
    from app.requests.models import RequestItem
    from app.resources.models import Resource
    from app.tracking.models import TrackingGroup

    rows = (
        db.query(TrackingGroup, Contribution, Resource, User)
        .join(Contribution, Contribution.id == TrackingGroup.contribution_id)
        .join(RequestItem, RequestItem.id == Contribution.request_item_id)
        .join(Resource, Resource.id == RequestItem.resource_id)
        .join(User, User.id == Contribution.maker_id)
        .filter(TrackingGroup.id.in_(group_ids))
        .all()
    )
    facts: dict[UUID, _PackageFacts] = {}
    for group, contribution, resource, maker in rows:
        facts[group.id] = _PackageFacts(
            resource_name=resource.name,
            quantity=contribution.quantity,
            status=str(contribution.status),
            maker=maker,
            tracking_token=group.tracking_token,
        )
    return facts


def list_contents(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    viewer: User | None,
) -> schemas.ShipmentContentsResponse:
    """Build a shipment's manifest, itemised only for its custodians (FR-146).

    Aggregate counts are public — a box's size is printed on its label anyway,
    and the community should be able to see that aid is moving. The **lines**
    are not: a label is a physical object anyone can photograph, and holding
    one must not turn into a roster of who sent what. So the itemised manifest
    goes to the staff of the box's origin or destination center (plus
    maintainers/admins), who need it to check a delivery against a list.

    Everyone else gets the totals plus ``hidden_count`` — how many packages
    were withheld, without describing any of them.
    """
    shipment = get_or_raise(db, collection_center_id, shipment_id)
    can_manage = can_manage_shipment(db, shipment, viewer)

    direct = (
        db.query(models.ShipmentContent)
        .filter(
            models.ShipmentContent.shipment_id == shipment.id,
            models.ShipmentContent.active.is_(True),
        )
        .order_by(models.ShipmentContent.created_at.asc())
        .all()
    )
    # Totals span the whole subtree, so a relay box reports what it really
    # carries rather than just the boxes visible on its top layer.
    all_group_ids = contained_group_ids(db, shipment.id)
    facts = _package_facts(db, all_group_ids)

    entries: list[schemas.ShipmentContentEntry] = []
    if can_manage:
        for row in direct:
            if row.tracking_group_id is not None:
                entries.append(_package_entry(row, facts.get(row.tracking_group_id)))
            elif row.child_shipment_id is not None:
                entries.append(_box_entry(db, row))

    return schemas.ShipmentContentsResponse(
        shipment_id=shipment.id,
        contents_total=len(direct),
        child_count=sum(1 for r in direct if r.child_shipment_id is not None),
        package_count=len(all_group_ids),
        # The physical load, shown to everyone: it is printed on the label.
        units_total=sum(f.quantity for f in facts.values()),
        hidden_count=0 if can_manage else len(all_group_ids),
        entries=entries,
        can_manage_contents=can_manage,
    )


def _package_entry(
    row: models.ShipmentContent, facts: _PackageFacts | None
) -> schemas.ShipmentContentEntry:
    """One package line. Only ever built for a custodian of the box."""
    if facts is None:  # pragma: no cover - a live content row always resolves
        return schemas.ShipmentContentEntry(
            id=row.id,
            kind=schemas.ContentKind.PACKAGE,
            redacted=True,
            added_at=row.created_at,
        )
    return schemas.ShipmentContentEntry(
        id=row.id,
        kind=schemas.ContentKind.PACKAGE,
        tracking_group_id=row.tracking_group_id,
        tracking_token=facts.tracking_token,
        resource_name=facts.resource_name,
        quantity=facts.quantity,
        contribution_status=facts.status,
        maker_username=facts.maker.username,
        maker_full_name=facts.maker.full_name,
        maker_avatar_url=facts.maker.avatar_url,
        maker_avatar_crop_x=facts.maker.avatar_crop_x,
        maker_avatar_crop_y=facts.maker.avatar_crop_y,
        maker_avatar_crop_w=facts.maker.avatar_crop_w,
        maker_avatar_crop_h=facts.maker.avatar_crop_h,
        added_at=row.created_at,
    )


def _box_entry(
    db: Session, row: models.ShipmentContent
) -> schemas.ShipmentContentEntry:
    """One nested-box line. Boxes are public, so nothing here is redacted."""
    assert row.child_shipment_id is not None
    child = db.get(models.Shipment, row.child_shipment_id)
    return schemas.ShipmentContentEntry(
        id=row.id,
        kind=schemas.ContentKind.BOX,
        child_shipment_id=row.child_shipment_id,
        child_status=child.status if child else None,
        child_destination=child.destination if child else None,
        child_tracking_token=child.tracking_token if child else None,
        child_package_count=len(contained_group_ids(db, row.child_shipment_id)),
        added_at=row.created_at,
    )


class OpenBox(NamedTuple):
    """An open box plus the centre it belongs to, for the scan-surface picker."""

    shipment_id: UUID
    collection_center_id: UUID
    label: str


def open_boxes_for(
    db: Session, actor: User | None, *, exclude_ids: set[UUID] | None = None
) -> list[OpenBox]:
    """Boxes the actor could pack something into, right now.

    Every box at a center they staff that is still open (``receiving`` or
    ``arrived``), newest first. ``exclude_ids`` drops boxes that would form a
    cycle — the scanned box itself and everything inside it — so an impossible
    choice is never offered rather than being rejected after the fact.

    Empty for guests and for anyone who staffs no center, which is what keeps
    the packing UI invisible to the makers and passers-by who scan these QRs.
    """
    from app.collection_centers.models import CollectionCenter

    if actor is None:
        return []
    centers = cc_service.list_my_centers(db, actor)
    if not centers:
        return []
    names = {center.id: center.name for center in centers}
    rows = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.collection_center_id.in_(list(names)),
            models.Shipment.active.is_(True),
            models.Shipment.status.in_(PACKABLE_STATUSES),
        )
        .order_by(models.Shipment.shipment_date.desc())
        .all()
    )
    skip = exclude_ids or set()

    destination_ids = {
        row.destination_collection_center_id
        for row in rows
        if row.destination_collection_center_id is not None
    }
    destinations: dict[UUID, str] = {}
    if destination_ids:
        destinations = {
            c.id: c.name
            for c in db.query(CollectionCenter)
            .filter(CollectionCenter.id.in_(list(destination_ids)))
            .all()
        }

    boxes: list[OpenBox] = []
    for row in rows:
        if row.id in skip:
            continue
        where = (
            (
                destinations.get(row.destination_collection_center_id)
                if row.destination_collection_center_id is not None
                else None
            )
            or row.destination
            or "?"
        )
        boxes.append(
            OpenBox(
                shipment_id=row.id,
                collection_center_id=row.collection_center_id,
                label=(
                    f"{names[row.collection_center_id]} · "
                    f"{row.shipment_date.isoformat()} -> {where}"
                ),
            )
        )
    return boxes


def holder_of(
    db: Session,
    *,
    tracking_group_id: UUID | None = None,
    child_shipment_id: UUID | None = None,
) -> tuple[UUID, str, str] | None:
    """The box currently holding this package/box: ``(id, label, token)``."""
    row = _active_parent_row(
        db, tracking_group_id=tracking_group_id, child_shipment_id=child_shipment_id
    )
    if row is None:
        return None
    box = db.get(models.Shipment, row.shipment_id)
    if box is None:  # pragma: no cover - shipments are soft-deleted, never gone
        return None
    return box.id, destination_label(db, box), box.tracking_token


def _resolve_packable_token(db: Session, token: str) -> tuple[UUID | None, UUID | None]:
    """Resolve a scanned token to ``(tracking_group_id, child_shipment_id)``.

    Accepts any of the three QR levels, because staff scan whatever is on the
    thing in their hand. A **unit** token resolves to the package it belongs
    to: packages are the unit of packing, so scanning any one splint of a
    283-piece contribution packs the whole contribution. A **package** token
    resolves to itself, and a **box** token nests that box.

    Tolerates a full ``https://…/track/<token>`` URL, which is what a phone
    camera produces and a staffer pastes.
    """
    from app.tracking.exceptions import TrackingNotFoundExceptionError
    from app.tracking.models import TrackingGroup, TrackingItem

    raw = token.strip().rstrip("/")
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    raw = raw.split("?", 1)[0]

    item = (
        db.query(TrackingItem)
        .filter(TrackingItem.tracking_token == raw, TrackingItem.active.is_(True))
        .first()
    )
    if item is not None:
        return item.group_id, None

    group = (
        db.query(TrackingGroup)
        .filter(TrackingGroup.tracking_token == raw, TrackingGroup.active.is_(True))
        .first()
    )
    if group is not None:
        return group.id, None

    box = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.tracking_token == raw,
            models.Shipment.active.is_(True),
        )
        .first()
    )
    if box is not None:
        return None, box.id

    raise TrackingNotFoundExceptionError(raw)


def _assert_packable(shipment: models.Shipment) -> None:
    """Contents change only while the box is open at one end of its journey."""
    if shipment.status not in PACKABLE_STATUSES:
        raise ShipmentLockedExceptionError(shipment.status)


def _assert_not_already_packed(
    db: Session,
    *,
    tracking_group_id: UUID | None = None,
    child_shipment_id: UUID | None = None,
) -> None:
    """Pre-empt the partial unique index with a message that names the holder.

    The index would reject the insert anyway, but as an opaque
    ``IntegrityError``. Staff need to know *which* box already has it so they
    can go and unpack it.
    """
    holder = _active_parent_row(
        db, tracking_group_id=tracking_group_id, child_shipment_id=child_shipment_id
    )
    if holder is not None:
        raise AlreadyPackedExceptionError(holder.shipment_id)


def _assert_nestable(db: Session, parent: models.Shipment, child_id: UUID) -> None:
    """Reject nesting that would create a cycle or an over-deep chain."""
    if child_id == parent.id:
        raise ShipmentCycleExceptionError
    # Packing the parent into the child's subtree would close a loop, and every
    # walk below would then depend on its depth cap to terminate.
    if parent.id in descendant_shipment_ids(db, child_id):
        raise ShipmentCycleExceptionError
    above = len(ancestor_shipment_ids(db, shipment_id=parent.id))
    below = _subtree_height(db, child_id)
    # boxes in the resulting chain: ancestors + parent + child + child's subtree
    if above + 2 + below > MAX_SHIPMENT_DEPTH:
        raise ShipmentTooDeepExceptionError


def add_content(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    payload: schemas.ShipmentContentCreate,
    actor: User,
) -> models.ShipmentContent:
    """Pack a package or another box into this shipment (FR-138)."""
    shipment = get_or_raise(db, collection_center_id, shipment_id)
    _assert_can_manage_shipment(db, shipment, actor)
    _assert_packable(shipment)

    group_id, child_id = payload.tracking_group_id, payload.child_shipment_id
    if payload.tracking_token is not None:
        group_id, child_id = _resolve_packable_token(db, payload.tracking_token)

    if child_id is not None:
        # Loaded unscoped: a relay center nests a box that belongs to the
        # *upstream* center, so the child is normally not one of ours.
        child = (
            db.query(models.Shipment)
            .filter(models.Shipment.id == child_id, models.Shipment.active.is_(True))
            .first()
        )
        if child is None:
            raise ShipmentNotFoundExceptionError(child_id)
        _assert_nestable(db, shipment, child_id)
        _assert_not_already_packed(db, child_shipment_id=child_id)
    else:
        assert group_id is not None
        _assert_group_exists(db, group_id)
        _assert_not_already_packed(db, tracking_group_id=group_id)

    content = models.ShipmentContent(
        shipment_id=shipment.id,
        tracking_group_id=group_id,
        child_shipment_id=child_id,
        added_by_id=actor.id,
    )
    db.add(content)
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor.id,
        action=ActivityAction.ITEM_ADDED,
        changes={"content_id": str(content.id)},
    )
    db.commit()
    db.refresh(content)
    return content


def _assert_group_exists(db: Session, group_id: UUID) -> None:
    from app.tracking.exceptions import TrackingNotFoundExceptionError
    from app.tracking.models import TrackingGroup

    exists = (
        db.query(TrackingGroup.id)
        .filter(TrackingGroup.id == group_id, TrackingGroup.active.is_(True))
        .first()
    )
    if exists is None:
        raise TrackingNotFoundExceptionError(str(group_id))


def remove_content(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    content_id: UUID,
    actor: User,
) -> None:
    """Unpack one manifest line (soft delete, FR-147)."""
    shipment = get_or_raise(db, collection_center_id, shipment_id)
    _assert_can_manage_shipment(db, shipment, actor)
    _assert_packable(shipment)
    content = (
        db.query(models.ShipmentContent)
        .filter(
            models.ShipmentContent.id == content_id,
            models.ShipmentContent.shipment_id == shipment.id,
            models.ShipmentContent.active.is_(True),
        )
        .first()
    )
    if content is None:
        raise ShipmentContentNotFoundExceptionError(content_id)
    _retire_content(content, actor)
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor.id,
        action=ActivityAction.UPDATED,
        changes={"content_removed": str(content_id)},
    )
    db.commit()


def _retire_content(content: models.ShipmentContent, actor: User) -> None:
    """Soft-delete one manifest line, stamping who took it out and when."""
    content.active = False
    content.removed_by_id = actor.id
    content.removed_at = datetime.now(UTC)


def release_contents(db: Session, shipment: models.Shipment, actor: User) -> int:
    """Free every direct manifest line of a box (flush only; no commit).

    Called when a box is cancelled or soft-deleted. Without it the partial
    unique indexes would keep every package inside marked as "already packed",
    trapping them in a box that is never going anywhere. Nested child boxes
    become free-standing again and keep their own contents.
    """
    rows = (
        db.query(models.ShipmentContent)
        .filter(
            models.ShipmentContent.shipment_id == shipment.id,
            models.ShipmentContent.active.is_(True),
        )
        .all()
    )
    for row in rows:
        _retire_content(row, actor)
    db.flush()
    return len(rows)


def delete_shipment(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: User,
) -> None:
    """Soft-delete a shipment (effective member or maintainer/admin)."""
    _assert_can_manage(db, collection_center_id, actor)
    shipment = get_or_raise(db, collection_center_id, shipment_id)
    shipment.active = False
    # Free whatever was inside, or the partial unique indexes would keep every
    # package marked as "already packed" into a box that no longer exists.
    release_contents(db, shipment, actor)
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor.id,
        action=ActivityAction.DELETED,
        changes={},
    )
    db.commit()
