"""Contribution lifecycle business logic (Phase 4).

Implements the five-state machine (FR-052), the FR-126 auto-receive, the
FR-055 stale-claim expiry, and the helper the requests domain calls to
release still-``claimed`` Contributions when an item or campaign closes.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.collection_centers import service as cc_service
from app.collection_centers.constants import CollectionCenterStatus
from app.users.models import User

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
    """List the caller's Contributions enriched with Part + Request context."""
    from app.parts.models import Part
    from app.requests.models import Request, RequestItem

    query = (
        db.query(
            models.Contribution, Request.id, Request.title, Part.id, Part.name
        )
        .join(RequestItem, RequestItem.id == models.Contribution.request_item_id)
        .join(Request, Request.id == RequestItem.request_id)
        .join(Part, Part.id == RequestItem.part_id)
        .filter(
            models.Contribution.maker_id == actor.id,
            models.Contribution.active.is_(True),
        )
    )
    if status is not None:
        query = query.filter(models.Contribution.status == status)
    rows = query.order_by(models.Contribution.claimed_at.desc()).all()

    return [
        schemas.MyContributionResponse(
            **schemas.ContributionResponse.model_validate(contribution).model_dump(),
            request_id=request_id,
            request_title=request_title,
            part_id=part_id,
            part_name=part_name,
        )
        for contribution, request_id, request_title, part_id, part_name in rows
    ]


def create_contribution(
    db: Session, payload: schemas.ContributionCreate, actor: User
) -> models.Contribution:
    """Claim a quantity of an open RequestItem at a center (FR-050/051)."""
    from app.requests.constants import RequestStatus
    from app.requests.service import get_item_or_raise, get_request_or_raise

    item = get_item_or_raise(db, payload.request_item_id)
    request = get_request_or_raise(db, item.request_id)
    if item.status != RequestStatus.OPEN or request.status != RequestStatus.OPEN:
        raise RequestItemNotOpenExceptionError

    # The drop-off center is optional at claim time; validate it only when
    # provided so makers can commit before they have one (set it later).
    collection_center_id = None
    if payload.collection_center_id is not None:
        cc = cc_service.get_or_raise(db, payload.collection_center_id)
        if not (
            cc.verified and cc.active and cc.status == CollectionCenterStatus.ACTIVE
        ):
            raise CenterNotAvailableExceptionError
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
    db.commit()
    db.refresh(contribution)
    return contribution


def update_contribution(
    db: Session, contribution_id: UUID, payload: schemas.ContributionUpdate, actor: User
) -> models.Contribution:
    """Edit a claimed Contribution (FR-057); allow setting the center later.

    Quantity/notes are locked once the Contribution leaves ``claimed``; the
    drop-off center may also be assigned while ``printed`` (before delivery).
    """
    contribution = _get_maker_contribution(db, contribution_id, actor)
    data = payload.model_dump(exclude_unset=True)

    if ("quantity" in data or "notes" in data) and (
        contribution.status != ContributionStatus.CLAIMED
    ):
        raise ContributionLockedExceptionError

    if "collection_center_id" in data:
        if contribution.status not in (
            ContributionStatus.CLAIMED,
            ContributionStatus.PRINTED,
        ):
            raise ContributionLockedExceptionError
        center_id = data["collection_center_id"]
        if center_id is not None:
            cc = cc_service.get_or_raise(db, center_id)
            if not (
                cc.verified
                and cc.active
                and cc.status == CollectionCenterStatus.ACTIVE
            ):
                raise CenterNotAvailableExceptionError

    for field, value in data.items():
        setattr(contribution, field, value)
    db.commit()
    db.refresh(contribution)
    return contribution


def mark_printed(
    db: Session, contribution_id: UUID, actor: User
) -> models.Contribution:
    """Advance ``claimed -> printed`` (maker only, FR-053)."""
    contribution = _get_maker_contribution(db, contribution_id, actor)
    if contribution.status != ContributionStatus.CLAIMED:
        raise InvalidTransitionExceptionError(
            contribution.status, ContributionStatus.PRINTED
        )
    contribution.status = ContributionStatus.PRINTED
    contribution.printed_at = datetime.now(UTC)
    db.commit()
    db.refresh(contribution)
    return contribution


def mark_delivered(
    db: Session, contribution_id: UUID, actor: User
) -> models.Contribution:
    """Advance ``printed -> delivered``; auto-receive per FR-126."""
    contribution = _get_maker_contribution(db, contribution_id, actor)
    if contribution.status != ContributionStatus.PRINTED:
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
    db.commit()
    db.refresh(contribution)
    return contribution


def release(db: Session, contribution_id: UUID, actor: User) -> models.Contribution:
    """Release a ``claimed`` or ``printed`` Contribution (maker, FR-054)."""
    contribution = _get_maker_contribution(db, contribution_id, actor)
    if contribution.status not in (
        ContributionStatus.CLAIMED,
        ContributionStatus.PRINTED,
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
