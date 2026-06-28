"""Request + RequestItem business logic: CRUD, cascades, progress (Phase 4)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.permissions import (
    assert_caller_can_own_on_behalf_of,
    effective_requester_user_ids,
    has_global_override,
)
from app.users.models import User

from . import models, schemas
from .constants import ClosedReason, RequestStatus
from .exceptions import (
    DuplicatePartExceptionError,
    ItemHasContributionsExceptionError,
    ItemRequestMismatchExceptionError,
    NotEffectiveRequesterExceptionError,
    RequestItemNotFoundExceptionError,
    RequestNeedsItemExceptionError,
    RequestNotFoundExceptionError,
    RequestNotOpenExceptionError,
)


def get_request_or_raise(db: Session, request_id: UUID) -> models.Request:
    """Return a Request by id or raise ``NotFound``."""
    request = db.query(models.Request).filter(models.Request.id == request_id).first()
    if request is None:
        raise RequestNotFoundExceptionError(request_id)
    return request


def get_item_or_raise(db: Session, item_id: UUID) -> models.RequestItem:
    """Return a RequestItem by id or raise ``NotFound``."""
    item = db.query(models.RequestItem).filter(models.RequestItem.id == item_id).first()
    if item is None:
        raise RequestItemNotFoundExceptionError(item_id)
    return item


def is_effective_requester(db: Session, request: models.Request, user: User) -> bool:
    """Return True if the user has requester powers (or a global override)."""
    return has_global_override(user) or user.id in effective_requester_user_ids(
        db, request
    )


def _assert_effective_requester(
    db: Session, request: models.Request, user: User
) -> None:
    if not is_effective_requester(db, request, user):
        raise NotEffectiveRequesterExceptionError


def _assert_open(request: models.Request) -> None:
    if request.status != RequestStatus.OPEN:
        raise RequestNotOpenExceptionError


def _assert_part_active(db: Session, part_id: UUID) -> None:
    """Validate that a RequestItem references an active Part (FR-120)."""
    from app.parts.constants import PartStatus
    from app.parts.exceptions import PartDiscontinuedExceptionError
    from app.parts.service import get_or_raise as get_part_or_raise

    part = get_part_or_raise(db, part_id)
    if not part.active or part.status != PartStatus.ACTIVE:
        raise PartDiscontinuedExceptionError(part_id)


def _assert_part_not_duplicate(db: Session, request_id: UUID, part_id: UUID) -> None:
    """Reject a Part already present as an active item on the Request (FR-120)."""
    exists = (
        db.query(models.RequestItem)
        .filter(
            models.RequestItem.request_id == request_id,
            models.RequestItem.part_id == part_id,
            models.RequestItem.active.is_(True),
        )
        .first()
    )
    if exists is not None:
        raise DuplicatePartExceptionError(part_id)


# ---------------------------------------------------------------------------
# Progress aggregation (the core per-item summary)
# ---------------------------------------------------------------------------


def compute_item_progress(
    db: Session, item: models.RequestItem
) -> schemas.RequestItemProgress:
    """Aggregate Contribution quantities into the item progress buckets.

    ``claimed`` = claimed + printed; ``at_center`` = delivered + received
    (FR-063); ``committed`` excludes ``released`` (FR-062); ``remaining`` is
    ``max(0, target - committed)`` or None for open-ended ("as many as
    possible") items.
    """
    from app.contributions.constants import ContributionStatus
    from app.contributions.models import Contribution

    rows = (
        db.query(
            Contribution.status,
            func.coalesce(func.sum(Contribution.quantity), 0),
        )
        .filter(
            Contribution.request_item_id == item.id,
            Contribution.active.is_(True),
        )
        .group_by(Contribution.status)
        .all()
    )
    by_status = {status: int(total) for status, total in rows}
    claimed = by_status.get(ContributionStatus.CLAIMED, 0) + by_status.get(
        ContributionStatus.PRINTED, 0
    )
    at_center = by_status.get(ContributionStatus.DELIVERED, 0) + by_status.get(
        ContributionStatus.RECEIVED, 0
    )
    committed = claimed + at_center
    remaining = max(0, item.quantity - committed) if item.quantity is not None else None
    return schemas.RequestItemProgress(
        target_quantity=item.quantity,
        claimed_quantity=claimed,
        at_center_quantity=at_center,
        committed_quantity=committed,
        remaining=remaining,
    )


def _item_response(
    db: Session, item: models.RequestItem
) -> schemas.RequestItemResponse:
    return schemas.RequestItemResponse(
        id=item.id,
        request_id=item.request_id,
        part_id=item.part_id,
        quantity=item.quantity,
        description=item.description,
        deadline=item.deadline,
        status=item.status,
        closed_reason=item.closed_reason,
        active=item.active,
        created_at=item.created_at,
        updated_at=item.updated_at,
        progress=compute_item_progress(db, item),
    )


def list_active_items(db: Session, request_id: UUID) -> list[models.RequestItem]:
    """Return the active items of a Request, oldest first."""
    return (
        db.query(models.RequestItem)
        .filter(
            models.RequestItem.request_id == request_id,
            models.RequestItem.active.is_(True),
        )
        .order_by(models.RequestItem.created_at.asc())
        .all()
    )


def build_detail(db: Session, request: models.Request) -> schemas.RequestDetailResponse:
    """Serialize a Request with its items and per-item progress."""
    items = [_item_response(db, i) for i in list_active_items(db, request.id)]
    return schemas.RequestDetailResponse(
        **schemas.RequestResponse.model_validate(request).model_dump(),
        items=items,
    )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def list_requests(
    db: Session, status: RequestStatus | None = None
) -> list[models.Request]:
    """List Requests (public). Defaults to ``open`` campaigns only."""
    query = db.query(models.Request).filter(models.Request.active.is_(True))
    query = query.filter(models.Request.status == (status or RequestStatus.OPEN))
    return query.order_by(models.Request.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def create_request(
    db: Session, payload: schemas.RequestCreate, actor: User
) -> models.Request:
    """Create a Request with at least one item (FR-038 / FR-119)."""
    requester_user_id, requester_organization_id = assert_caller_can_own_on_behalf_of(
        db, actor, payload.owner_organization_id
    )
    seen_part_ids: set[UUID] = set()
    for item in payload.items:
        if item.part_id in seen_part_ids:
            raise DuplicatePartExceptionError(item.part_id)
        seen_part_ids.add(item.part_id)
        _assert_part_active(db, item.part_id)

    request = models.Request(
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        requester_user_id=requester_user_id,
        requester_organization_id=requester_organization_id,
        created_by_id=actor.id,
        preferred_collection_center_ids=payload.preferred_collection_center_ids,
    )
    db.add(request)
    db.flush()
    for item in payload.items:
        db.add(
            models.RequestItem(
                request_id=request.id,
                part_id=item.part_id,
                quantity=item.quantity,
                description=item.description,
                deadline=item.deadline,
            )
        )
    write_audit(
        db, actor.id, AuditAction.CREATE_REQUEST, AuditTargetType.REQUEST, request.id
    )
    db.commit()
    db.refresh(request)
    return request


def update_request(
    db: Session, request_id: UUID, payload: schemas.RequestUpdate, actor: User
) -> models.Request:
    """Edit campaign metadata while the Request is open (FR-042)."""
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    _assert_open(request)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(request, field, value)
    db.commit()
    db.refresh(request)
    return request


def _close_item(
    db: Session, item: models.RequestItem, reason: str, actor: User
) -> None:
    """Close one open item and release its still-``claimed`` Contributions."""
    from app.contributions.service import release_claimed_for_item

    item.status = RequestStatus.CLOSED
    item.closed_at = datetime.now(UTC)
    item.closed_by_id = actor.id
    item.closed_reason = reason
    release_claimed_for_item(db, item.id, reason, actor)


def close_request(
    db: Session, request_id: UUID, reason: str | None, actor: User
) -> models.Request:
    """Close a Request, cascading open items + claimed Contributions (FR-049)."""
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    _assert_open(request)

    for item in list_active_items(db, request.id):
        if item.status == RequestStatus.OPEN:
            _close_item(db, item, ClosedReason.REQUEST_CLOSED, actor)

    request.status = RequestStatus.CLOSED
    request.closed_at = datetime.now(UTC)
    request.closed_by_id = actor.id
    request.closed_reason = reason or ClosedReason.MANUAL
    write_audit(
        db, actor.id, AuditAction.CLOSE_REQUEST, AuditTargetType.REQUEST, request.id
    )
    db.commit()
    db.refresh(request)
    return request


def add_item(
    db: Session, request_id: UUID, payload: schemas.RequestItemCreate, actor: User
) -> schemas.RequestItemResponse:
    """Add a new RequestItem to an open Request (FR-122)."""
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    _assert_open(request)
    _assert_part_active(db, payload.part_id)
    _assert_part_not_duplicate(db, request_id, payload.part_id)

    item = models.RequestItem(
        request_id=request.id,
        part_id=payload.part_id,
        quantity=payload.quantity,
        description=payload.description,
        deadline=payload.deadline,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_response(db, item)


def _get_item_in_request(
    db: Session, request_id: UUID, item_id: UUID
) -> models.RequestItem:
    item = get_item_or_raise(db, item_id)
    if item.request_id != request_id:
        raise ItemRequestMismatchExceptionError
    return item


def update_item(
    db: Session,
    request_id: UUID,
    item_id: UUID,
    payload: schemas.RequestItemUpdate,
    actor: User,
) -> schemas.RequestItemResponse:
    """Edit an open item's target/description/deadline (effective requester)."""
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    _assert_open(request)
    item = _get_item_in_request(db, request_id, item_id)
    if item.status != RequestStatus.OPEN:
        raise RequestNotOpenExceptionError

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.flush()
    # A new target may now be met (or not) — re-evaluate fulfillment.
    recompute_item_fulfillment(db, item)
    db.commit()
    db.refresh(item)
    return _item_response(db, item)


def remove_item(db: Session, request_id: UUID, item_id: UUID, actor: User) -> None:
    """Remove an item from an open Request (FR-123)."""
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    _assert_open(request)
    item = _get_item_in_request(db, request_id, item_id)

    active_items = list_active_items(db, request_id)
    if len(active_items) <= 1:
        raise RequestNeedsItemExceptionError
    if _item_has_active_contributions(db, item_id):
        raise ItemHasContributionsExceptionError

    item.active = False
    db.commit()


def close_item(
    db: Session, request_id: UUID, item_id: UUID, reason: str | None, actor: User
) -> schemas.RequestItemResponse:
    """Close one item without closing the parent Request (FR-124)."""
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    item = _get_item_in_request(db, request_id, item_id)
    if item.status == RequestStatus.OPEN:
        _close_item(db, item, reason or ClosedReason.REQUEST_ITEM_CLOSED, actor)
    recompute_request_status(db, request)
    db.commit()
    db.refresh(item)
    return _item_response(db, item)


def _item_has_active_contributions(db: Session, item_id: UUID) -> bool:
    from app.contributions.constants import ContributionStatus
    from app.contributions.models import Contribution

    active_states = (
        ContributionStatus.CLAIMED,
        ContributionStatus.PRINTED,
        ContributionStatus.DELIVERED,
        ContributionStatus.RECEIVED,
    )
    return (
        db.query(Contribution)
        .filter(
            Contribution.request_item_id == item_id,
            Contribution.active.is_(True),
            Contribution.status.in_(active_states),
        )
        .count()
        > 0
    )


def close_open_items_for_part(db: Session, part_id: UUID, actor: User) -> None:
    """Close all open items referencing a Part being force-archived (FR-077)."""
    items = (
        db.query(models.RequestItem)
        .filter(
            models.RequestItem.part_id == part_id,
            models.RequestItem.active.is_(True),
            models.RequestItem.status == RequestStatus.OPEN,
        )
        .all()
    )
    touched_request_ids: set[UUID] = set()
    for item in items:
        _close_item(db, item, ClosedReason.PART_ARCHIVED, actor)
        touched_request_ids.add(item.request_id)
    for request_id in touched_request_ids:
        recompute_request_status(db, get_request_or_raise(db, request_id))


# ---------------------------------------------------------------------------
# Fulfillment recompute (called by the contributions domain)
# ---------------------------------------------------------------------------


def recompute_item_fulfillment(db: Session, item: models.RequestItem) -> None:
    """Auto-fulfill an open item when delivered+received meets target (FR-121)."""
    if item.status != RequestStatus.OPEN or item.quantity is None:
        return
    progress = compute_item_progress(db, item)
    if progress.at_center_quantity >= item.quantity:
        item.status = RequestStatus.FULFILLED
        item.closed_at = datetime.now(UTC)
    request = get_request_or_raise(db, item.request_id)
    recompute_request_status(db, request)


def recompute_request_status(db: Session, request: models.Request) -> None:
    """Auto-fulfill an open Request when every item is fulfilled (FR-041)."""
    if request.status != RequestStatus.OPEN:
        return
    items = list_active_items(db, request.id)
    if items and all(i.status == RequestStatus.FULFILLED for i in items):
        request.status = RequestStatus.FULFILLED
        request.closed_at = datetime.now(UTC)
