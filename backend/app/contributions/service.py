"""Contribution lifecycle business logic (Phase 4).

Implements the five-state machine (FR-052), the FR-126 auto-receive, the
FR-055 stale-claim expiry, and the helper the requests domain calls to
release still-``claimed`` Contributions when an item or campaign closes.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.collection_centers import service as cc_service
from app.collection_centers.constants import CollectionCenterStatus
from app.users.models import User

if TYPE_CHECKING:
    from app.collection_centers.models import CollectionCenter
    from app.requests.models import RequestItem
    from app.users.schemas import ProfileProjectResponse

from . import models, schemas
from .constants import (
    STALE_CLAIM_DAYS,
    ContributionStatus,
    ReleasedReason,
)
from .exceptions import (
    CenterNotAvailableExceptionError,
    CenterRequiredExceptionError,
    ContributionLockedExceptionError,
    ContributionNotFoundExceptionError,
    InvalidTransitionExceptionError,
    NotReceiverExceptionError,
    NotTheMakerExceptionError,
    RequestItemNotOpenExceptionError,
)


def get_or_raise(db: Session, contribution_id: UUID) -> models.Contribution:
    """Return a Contribution by id or raise ``NotFound``."""
    contribution = (
        db.query(models.Contribution)
        .filter(models.Contribution.id == contribution_id)
        .first()
    )
    if contribution is None:
        raise ContributionNotFoundExceptionError(contribution_id)
    return contribution


def _get_maker_contribution(
    db: Session, contribution_id: UUID, actor: User
) -> models.Contribution:
    contribution = get_or_raise(db, contribution_id)
    if contribution.maker_id != actor.id:
        raise NotTheMakerExceptionError
    return contribution


def _recompute_item(db: Session, request_item_id: UUID) -> None:
    """Re-evaluate the parent item/request fulfillment after a transition."""
    from app.requests.service import get_item_or_raise, recompute_item_fulfillment

    # The session is autoflush=False; flush the just-changed Contribution so
    # the progress aggregation below reads its new status, not the stale row.
    db.flush()
    item = get_item_or_raise(db, request_item_id)
    recompute_item_fulfillment(db, item)


def list_my_contributions(
    db: Session, actor: User, status: ContributionStatus | None = None
) -> list[schemas.MyContributionResponse]:
    """List the caller's Contributions enriched with Resource + Request context."""
    from app.collection_centers.models import CollectionCenter
    from app.requests.models import Request, RequestItem
    from app.resources.models import Resource
    from app.tracking.models import TrackingGroup

    query = (
        db.query(
            models.Contribution,
            Request.id,
            Request.title,
            Request.preferred_collection_center_ids,
            RequestItem.preferred_collection_center_ids,
            RequestItem.item_number,
            RequestItem.unit,
            Resource.id,
            Resource.name,
            Resource.image_url,
            Resource.category,
            CollectionCenter.name,
            CollectionCenter.location_url,
            TrackingGroup.tracking_token,
        )
        .join(RequestItem, RequestItem.id == models.Contribution.request_item_id)
        .join(Request, Request.id == RequestItem.request_id)
        .join(Resource, Resource.id == RequestItem.resource_id)
        # A Contribution may not have a drop-off center yet, so LEFT JOIN.
        .outerjoin(
            CollectionCenter,
            CollectionCenter.id == models.Contribution.collection_center_id,
        )
        # Tracking is opt-in, so LEFT JOIN its group (null token = none yet).
        .outerjoin(
            TrackingGroup,
            (TrackingGroup.contribution_id == models.Contribution.id)
            & (TrackingGroup.active.is_(True)),
        )
        .filter(
            models.Contribution.maker_id == actor.id,
            models.Contribution.active.is_(True),
        )
    )
    if status is not None:
        query = query.filter(models.Contribution.status == status)
    rows = query.order_by(models.Contribution.claimed_at.desc()).all()

    def _effective_centers(
        request_pref: list[UUID], item_pref: list[UUID]
    ) -> list[UUID]:
        """Item's drop-off centers: its subset, or all when it names none."""
        allowed = set(request_pref)
        filtered = [cid for cid in item_pref if cid in allowed]
        return filtered or list(request_pref)

    return [
        schemas.MyContributionResponse(
            **schemas.ContributionResponse.model_validate(contribution).model_dump(),
            request_id=request_id,
            request_title=request_title,
            preferred_collection_center_ids=_effective_centers(request_pref, item_pref),
            item_number=item_number,
            item_unit=item_unit,
            resource_id=resource_id,
            resource_name=resource_name,
            resource_image_url=resource_image_url,
            resource_category=resource_category,
            collection_center_name=collection_center_name,
            collection_center_location_url=collection_center_location_url,
            tracking_token=tracking_token,
        )
        for (
            contribution,
            request_id,
            request_title,
            request_pref,
            item_pref,
            item_number,
            item_unit,
            resource_id,
            resource_name,
            resource_image_url,
            resource_category,
            collection_center_name,
            collection_center_location_url,
            tracking_token,
        ) in rows
    ]


def list_public_for_item(
    db: Session, request_item_id: UUID
) -> list[schemas.ItemCommitmentResponse]:
    """List active commitments on an item for its public detail page.

    Joined to the maker username (and drop-off center name), newest first.
    Omits the maker's private notes/tags.
    """
    from app.collection_centers.models import CollectionCenter

    rows = (
        db.query(models.Contribution, User.username, CollectionCenter.name)
        .join(User, User.id == models.Contribution.maker_id)
        .outerjoin(
            CollectionCenter,
            CollectionCenter.id == models.Contribution.collection_center_id,
        )
        .filter(
            models.Contribution.request_item_id == request_item_id,
            models.Contribution.active.is_(True),
        )
        .order_by(models.Contribution.claimed_at.desc())
        .all()
    )
    return [
        schemas.ItemCommitmentResponse(
            id=contribution.id,
            maker_username=username,
            quantity=contribution.quantity,
            status=contribution.status,
            collection_center_name=center_name,
            claimed_at=contribution.claimed_at,
            prepared_at=contribution.prepared_at,
            delivered_at=contribution.delivered_at,
            received_at=contribution.received_at,
        )
        for (contribution, username, center_name) in rows
    ]


def list_public_for_user(db: Session, user_id: UUID) -> "list[ProfileProjectResponse]":
    """List a user's public contributions for their profile "projects" card.

    One entry per active Contribution the user made, joined to its Request,
    item, Resource, and (optional) drop-off Center, newest activity first.
    Only contributions on **published** (``approved``) campaigns are returned,
    so an unpublished/private campaign never leaks through a public profile.
    """
    from app.collection_centers.models import CollectionCenter
    from app.requests.constants import ModerationStatus
    from app.requests.models import Request, RequestItem
    from app.resources.models import Resource
    from app.users.schemas import ProfileProjectResponse

    rows = (
        db.query(
            models.Contribution,
            Request.id,
            Request.title,
            RequestItem.item_number,
            RequestItem.unit,
            Resource.id,
            Resource.name,
            Resource.image_url,
            Resource.category,
            CollectionCenter.name,
            CollectionCenter.country,
        )
        .join(RequestItem, RequestItem.id == models.Contribution.request_item_id)
        .join(Request, Request.id == RequestItem.request_id)
        .join(Resource, Resource.id == RequestItem.resource_id)
        .outerjoin(
            CollectionCenter,
            CollectionCenter.id == models.Contribution.collection_center_id,
        )
        .filter(
            models.Contribution.maker_id == user_id,
            models.Contribution.active.is_(True),
            Request.active.is_(True),
            Request.moderation_status == ModerationStatus.APPROVED,
        )
        .order_by(models.Contribution.updated_at.desc())
        .all()
    )
    return [
        ProfileProjectResponse(
            request_id=request_id,
            request_title=request_title,
            item_number=item_number,
            resource_id=resource_id,
            resource_name=resource_name,
            resource_image_url=resource_image_url,
            resource_category=resource_category,
            status=contribution.status,
            quantity=contribution.quantity,
            unit=unit,
            collection_center_name=center_name,
            collection_center_country=center_country,
            last_activity_at=contribution.updated_at,
        )
        for (
            contribution,
            request_id,
            request_title,
            item_number,
            unit,
            resource_id,
            resource_name,
            resource_image_url,
            resource_category,
            center_name,
            center_country,
        ) in rows
    ]


def _record_item_activity(
    db: Session,
    contribution: models.Contribution,
    actor: User,
    *,
    to_status: ContributionStatus | None = None,
    created: bool = False,
    quantity_from: int | None = None,
) -> None:
    """Log a commitment event on the parent item's public activity timeline.

    ``created`` records the claim, ``quantity_from`` a resize of an existing
    commitment; otherwise a status change to ``to_status``. Feeds the item
    detail page's activity feed + last-activity timestamp and, via ``record``'s
    fan-out, notifies item watchers. Function-local imports keep the activity
    domain out of the import cycle.
    """
    from app.activity.constants import ActivityAction, EntityType
    from app.activity.service import record

    changes: dict[str, object] = {"quantity": contribution.quantity}
    if quantity_from is not None:
        action = ActivityAction.UPDATED
        changes["quantity"] = {"from": quantity_from, "to": contribution.quantity}
    elif created:
        action = ActivityAction.CREATED
    else:
        action = ActivityAction.STATUS_CHANGED
    if to_status is not None:
        changes["status"] = {"to": to_status.value}
    record(
        db,
        entity_type=EntityType.REQUEST_ITEM,
        entity_id=contribution.request_item_id,
        actor_user_id=actor.id,
        action=action,
        changes=changes,
    )


def create_contribution(
    db: Session, payload: schemas.ContributionCreate, actor: User
) -> models.Contribution:
    """Claim a quantity of a RequestItem at a center (FR-050/051).

    Commitments are allowed even when the item/campaign is fulfilled or closed:
    a maker who already printed a part or bought supplies can still send them
    (lower priority). Closed items/campaigns keep their status — the fulfilment
    recompute ignores non-open items — so the commitment simply flows through
    the normal lifecycle (My Contributions, tracking QR, etc.). Only archived
    (removed) items/campaigns reject new commitments.
    """
    from app.requests.constants import ModerationStatus
    from app.requests.exceptions import RequestNotPublishedExceptionError
    from app.requests.service import get_item_or_raise, get_request_or_raise

    item = get_item_or_raise(db, payload.request_item_id)
    request = get_request_or_raise(db, item.request_id)
    if not item.active or not request.active:
        raise RequestItemNotOpenExceptionError
    # An unpublished campaign is invisible, but its item ids would still be
    # claimable by anyone who saw a pre-publication link — close that hole.
    if request.moderation_status != ModerationStatus.APPROVED:
        raise RequestNotPublishedExceptionError

    # The drop-off center is optional at claim time; validate it only when
    # provided so makers can commit before they have one (set it later).
    collection_center_id = None
    if payload.collection_center_id is not None:
        cc = cc_service.get_or_raise(db, payload.collection_center_id)
        _assert_center_available_for_item(db, cc, item)
        collection_center_id = cc.id

    contribution = models.Contribution(
        request_item_id=item.id,
        maker_id=actor.id,
        collection_center_id=collection_center_id,
        quantity=payload.quantity,
        notes=payload.notes,
        status=ContributionStatus.CLAIMED,
        claimed_at=datetime.now(UTC),
    )
    db.add(contribution)
    db.flush()
    _record_item_activity(db, contribution, actor, created=True)
    db.commit()
    db.refresh(contribution)
    return contribution


def _assert_center_available_for_item(
    db: Session, cc: "CollectionCenter", item: "RequestItem"
) -> None:
    """Validate a drop-off center for a contribution on ``item`` (FR-064).

    A center must be live and operational. A **listed** (public directory)
    center must also be verified. An **unlisted** (private, request-specific)
    center skips public verification but is only usable when it is among the
    item's effective preferred centers, so a private location is confined to
    the requests that reference it.
    """
    from app.requests.service import (
        effective_item_center_ids,
        get_request_or_raise,
    )

    if not (cc.active and cc.status == CollectionCenterStatus.ACTIVE):
        raise CenterNotAvailableExceptionError
    if cc.listed:
        if not cc.verified:
            raise CenterNotAvailableExceptionError
        return
    request = get_request_or_raise(db, item.request_id)
    if cc.id not in effective_item_center_ids(item, request):
        raise CenterNotAvailableExceptionError


def update_contribution(
    db: Session, contribution_id: UUID, payload: schemas.ContributionUpdate, actor: User
) -> models.Contribution:
    """Edit an undelivered Contribution (FR-057); allow setting the center later.

    Makers routinely discover mid-print that they can manage more (or fewer)
    units than they first committed to, so quantity/notes/center stay editable
    for the whole pre-delivery window (``claimed`` and ``prepared``) and lock
    once the units are physically handed over (``delivered`` onwards).

    A quantity change also reconciles the Contribution's per-unit tracking QRs
    (see :func:`app.tracking.service.sync_units`) and lands on the item's
    public activity timeline, so watchers see the commitment move.
    """
    from app.tracking.service import sync_units

    contribution = _get_maker_contribution(db, contribution_id, actor)
    data = payload.model_dump(exclude_unset=True)
    editable = (ContributionStatus.CLAIMED, ContributionStatus.PREPARED)

    if (
        "quantity" in data or "notes" in data or "collection_center_id" in data
    ) and contribution.status not in editable:
        raise ContributionLockedExceptionError

    if "collection_center_id" in data:
        center_id = data["collection_center_id"]
        if center_id is not None:
            from app.requests.service import get_item_or_raise

            cc = cc_service.get_or_raise(db, center_id)
            item = get_item_or_raise(db, contribution.request_item_id)
            _assert_center_available_for_item(db, cc, item)

    previous_quantity = contribution.quantity
    for field, value in data.items():
        setattr(contribution, field, value)

    quantity_changed = contribution.quantity != previous_quantity
    if quantity_changed:
        sync_units(db, contribution)
        _record_item_activity(db, contribution, actor, quantity_from=previous_quantity)
        write_audit(
            db,
            actor_id=actor.id,
            action=AuditAction.UPDATE_CONTRIBUTION_QUANTITY,
            target_type=AuditTargetType.CONTRIBUTION,
            target_id=contribution.id,
            reason=f"{previous_quantity} -> {contribution.quantity}",
        )

    # No fulfillment recompute: an item only auto-fulfills on its delivered +
    # received total (FR-121), and this edit is gated to the pre-delivery
    # window. The claimed/committed totals are summed live per read.
    db.commit()
    db.refresh(contribution)
    return contribution


def mark_prepared(
    db: Session, contribution_id: UUID, actor: User
) -> models.Contribution:
    """Advance ``claimed -> prepared`` (maker only, FR-053)."""
    contribution = _get_maker_contribution(db, contribution_id, actor)
    if contribution.status != ContributionStatus.CLAIMED:
        raise InvalidTransitionExceptionError(
            contribution.status, ContributionStatus.PREPARED
        )
    contribution.status = ContributionStatus.PREPARED
    contribution.prepared_at = datetime.now(UTC)
    _record_item_activity(
        db, contribution, actor, to_status=ContributionStatus.PREPARED
    )
    db.commit()
    db.refresh(contribution)
    return contribution


def _resource_category_for_item(db: Session, request_item_id: UUID) -> str:
    """Return the ``resource_category`` of the item's Resource."""
    from app.requests.models import RequestItem
    from app.resources.models import Resource

    return (
        db.query(Resource.category)
        .join(RequestItem, RequestItem.resource_id == Resource.id)
        .filter(RequestItem.id == request_item_id)
        .scalar()
    )


def mark_delivered(
    db: Session, contribution_id: UUID, actor: User
) -> models.Contribution:
    """Advance to ``delivered``; auto-receive per FR-126.

    3D-print contributions go ``prepared -> delivered``. Supplies (any
    non-``print_3d`` Resource) have no "prepared" step, so they advance
    straight from ``claimed`` (a maker can also deliver an already-prepared
    supply, e.g. legacy state).
    """
    from app.resources.constants import ResourceCategory

    contribution = _get_maker_contribution(db, contribution_id, actor)
    is_print = (
        _resource_category_for_item(db, contribution.request_item_id)
        == ResourceCategory.PRINT_3D
    )
    allowed_from = (
        (ContributionStatus.PREPARED,)
        if is_print
        else (ContributionStatus.CLAIMED, ContributionStatus.PREPARED)
    )
    if contribution.status not in allowed_from:
        raise InvalidTransitionExceptionError(
            contribution.status, ContributionStatus.DELIVERED
        )
    if contribution.collection_center_id is None:
        raise CenterRequiredExceptionError
    now = datetime.now(UTC)
    contribution.status = ContributionStatus.DELIVERED
    contribution.delivered_at = now

    cc = cc_service.get_or_raise(db, contribution.collection_center_id)
    if cc_service.is_effective_member(db, cc, actor):
        contribution.status = ContributionStatus.RECEIVED
        contribution.received_at = now
        contribution.received_by_id = actor.id
        contribution.auto_received = True
        write_audit(
            db,
            actor.id,
            AuditAction.AUTO_RECEIVE_CONTRIBUTION,
            AuditTargetType.CONTRIBUTION,
            contribution.id,
        )

    _recompute_item(db, contribution.request_item_id)
    _record_item_activity(db, contribution, actor, to_status=contribution.status)
    db.commit()
    db.refresh(contribution)
    return contribution


def confirm_received(
    db: Session, contribution_id: UUID, actor: User
) -> models.Contribution:
    """Confirm ``delivered -> received`` (effective CC member, FR-056)."""
    contribution = get_or_raise(db, contribution_id)
    if contribution.status != ContributionStatus.DELIVERED:
        raise InvalidTransitionExceptionError(
            contribution.status, ContributionStatus.RECEIVED
        )
    # A delivered Contribution always has a center (mark_delivered enforces it).
    if contribution.collection_center_id is None:  # pragma: no cover - invariant
        raise CenterRequiredExceptionError
    cc = cc_service.get_or_raise(db, contribution.collection_center_id)
    if not cc_service.is_effective_member(db, cc, actor):
        raise NotReceiverExceptionError
    contribution.status = ContributionStatus.RECEIVED
    contribution.received_at = datetime.now(UTC)
    contribution.received_by_id = actor.id
    write_audit(
        db,
        actor.id,
        AuditAction.CONFIRM_RECEIVED,
        AuditTargetType.CONTRIBUTION,
        contribution.id,
    )
    _recompute_item(db, contribution.request_item_id)
    _record_item_activity(
        db, contribution, actor, to_status=ContributionStatus.RECEIVED
    )
    db.commit()
    db.refresh(contribution)
    return contribution


def release(db: Session, contribution_id: UUID, actor: User) -> models.Contribution:
    """Release a ``claimed`` or ``prepared`` Contribution (maker, FR-054)."""
    contribution = _get_maker_contribution(db, contribution_id, actor)
    if contribution.status not in (
        ContributionStatus.CLAIMED,
        ContributionStatus.PREPARED,
    ):
        raise InvalidTransitionExceptionError(
            contribution.status, ContributionStatus.RELEASED
        )
    contribution.status = ContributionStatus.RELEASED
    contribution.released_at = datetime.now(UTC)
    contribution.released_reason = ReleasedReason.MANUAL
    write_audit(
        db,
        actor.id,
        AuditAction.RELEASE_CONTRIBUTION,
        AuditTargetType.CONTRIBUTION,
        contribution.id,
    )
    _recompute_item(db, contribution.request_item_id)
    _record_item_activity(
        db, contribution, actor, to_status=ContributionStatus.RELEASED
    )
    db.commit()
    db.refresh(contribution)
    return contribution


def release_claimed_for_item(
    db: Session, request_item_id: UUID, reason: str, actor: User
) -> None:
    """Release still-``claimed`` Contributions on an item (FR-049/124).

    Stages the changes on the session; the calling service commits them in
    the same transaction as the item/campaign close.
    """
    rows = (
        db.query(models.Contribution)
        .filter(
            models.Contribution.request_item_id == request_item_id,
            models.Contribution.active.is_(True),
            models.Contribution.status == ContributionStatus.CLAIMED,
        )
        .all()
    )
    now = datetime.now(UTC)
    for contribution in rows:
        contribution.status = ContributionStatus.RELEASED
        contribution.released_at = now
        contribution.released_reason = reason
        write_audit(
            db,
            actor.id,
            AuditAction.RELEASE_CONTRIBUTION,
            AuditTargetType.CONTRIBUTION,
            contribution.id,
            reason=reason,
        )


def expire_stale_claims(db: Session) -> int:
    """Release ``claimed`` Contributions older than ``STALE_CLAIM_DAYS`` (FR-055).

    Returns the number of Contributions expired. Audited under the system
    ``anonymous`` user since no human actor triggers the sweep.
    """
    from app.users.service import get_or_create_anonymous_user

    cutoff = datetime.now(UTC) - timedelta(days=STALE_CLAIM_DAYS)
    rows = (
        db.query(models.Contribution)
        .filter(
            models.Contribution.active.is_(True),
            models.Contribution.status == ContributionStatus.CLAIMED,
            models.Contribution.claimed_at < cutoff,
        )
        .all()
    )
    if not rows:
        return 0
    system_actor = get_or_create_anonymous_user(db)
    now = datetime.now(UTC)
    for contribution in rows:
        contribution.status = ContributionStatus.RELEASED
        contribution.released_at = now
        contribution.released_reason = ReleasedReason.EXPIRED
        write_audit(
            db,
            system_actor.id,
            AuditAction.EXPIRE_CONTRIBUTION,
            AuditTargetType.CONTRIBUTION,
            contribution.id,
        )
    db.commit()
    return len(rows)
