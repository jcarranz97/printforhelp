"""Request + RequestItem business logic: CRUD, cascades, progress (Phase 4)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.contributions.schemas import ItemCommitmentResponse

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.permissions import (
    assert_caller_can_own_on_behalf_of,
    effective_requester_user_ids,
    has_global_override,
)
from app.users.models import User

from . import models, schemas
from .constants import (
    SUBMITTABLE_STATUSES,
    ClosedReason,
    HelpState,
    ModerationStatus,
    RequestStatus,
)
from .exceptions import (
    ItemHasContributionsExceptionError,
    ItemRequestMismatchExceptionError,
    NotEffectiveRequesterExceptionError,
    RequestItemNotClosedExceptionError,
    RequestItemNotFoundExceptionError,
    RequestNeedsItemExceptionError,
    RequestNotApprovedExceptionError,
    RequestNotClosedExceptionError,
    RequestNotFoundExceptionError,
    RequestNotOpenExceptionError,
    RequestNotPendingExceptionError,
    RequestNotSubmittableExceptionError,
)


def list_beneficiary_suggestions(db: Session, limit: int = 100) -> list[str]:
    """Distinct ``beneficiary`` values from existing requests, for form typeahead.

    Powers the "Who is the project for?" autocomplete so a requester can reuse a
    beneficiary another project already helped (e.g. a recurring hospital or
    shelter). Ordered by how often each value is used (most common first), then
    alphabetically. Only non-empty values on active requests are surfaced.
    """
    rows = (
        db.query(models.Request.beneficiary)
        .filter(models.Request.beneficiary.isnot(None))
        .filter(models.Request.beneficiary != "")
        .filter(models.Request.active.is_(True))
        .group_by(models.Request.beneficiary)
        .order_by(func.count().desc(), models.Request.beneficiary.asc())
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


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


def can_view_request(db: Session, request: models.Request, viewer: User | None) -> bool:
    """Whether a viewer may read this campaign at all (the moderation gate).

    Only an ``approved`` campaign is public. Anything still in the moderation
    pipeline — draft, awaiting review, sent back, rejected — is readable solely
    by its effective requesters and by maintainers/admins. This is the single
    source of truth for that rule; every read path funnels through it so a
    leaked URL is worthless to anyone else.
    """
    if request.moderation_status == ModerationStatus.APPROVED:
        return True
    if viewer is None:
        return False
    return is_effective_requester(db, request, viewer)


def assert_can_view_request(
    db: Session, request: models.Request, viewer: User | None
) -> None:
    """Raise 404 (not 403) when a viewer may not see an unpublished campaign.

    404 rather than 403 so the response cannot be used to confirm that a given
    campaign id exists.
    """
    if not can_view_request(db, request, viewer):
        raise RequestNotFoundExceptionError(request.id)


def _assert_effective_requester(
    db: Session, request: models.Request, user: User
) -> None:
    if not is_effective_requester(db, request, user):
        raise NotEffectiveRequesterExceptionError


def _assert_open(request: models.Request) -> None:
    if request.status != RequestStatus.OPEN:
        raise RequestNotOpenExceptionError


def _assert_resource_active(db: Session, resource_id: UUID) -> None:
    """Validate that a RequestItem references an active Resource (FR-120)."""
    from app.resources.constants import ResourceStatus
    from app.resources.exceptions import ResourceDiscontinuedExceptionError
    from app.resources.service import get_or_raise as get_resource_or_raise

    resource = get_resource_or_raise(db, resource_id)
    if not resource.active or resource.status != ResourceStatus.ACTIVE:
        raise ResourceDiscontinuedExceptionError(resource_id)


# ---------------------------------------------------------------------------
# Progress aggregation (the core per-item summary)
# ---------------------------------------------------------------------------


def compute_item_progress(
    db: Session, item: models.RequestItem
) -> schemas.RequestItemProgress:
    """Aggregate Contribution quantities into the item progress buckets.

    ``claimed`` = claimed + prepared; ``at_center`` = delivered + received
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
        ContributionStatus.PREPARED, 0
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


def _countries_for_center_ids(db: Session, center_ids: list[UUID]) -> list[str]:
    """Distinct country values for a set of collection centers, sorted."""
    from app.collection_centers.models import CollectionCenter

    if not center_ids:
        return []
    rows = (
        db.query(CollectionCenter.country)
        .filter(CollectionCenter.id.in_(set(center_ids)))
        .distinct()
        .all()
    )
    return sorted({country for (country,) in rows})


def _item_response(
    db: Session,
    item: models.RequestItem,
    request: models.Request,
) -> schemas.RequestItemResponse:
    # The item's effective drop-off centers resolve against its Request's
    # preferred list, so the caller passes the owning Request.
    countries = _countries_for_center_ids(db, effective_item_center_ids(item, request))
    return schemas.RequestItemResponse(
        id=item.id,
        request_id=item.request_id,
        item_number=item.item_number,
        resource_id=item.resource_id,
        quantity=item.quantity,
        unit=item.unit,
        preferred_collection_center_ids=item.preferred_collection_center_ids,
        countries=countries,
        description=item.description,
        deadline=item.deadline,
        status=item.status,
        closed_reason=item.closed_reason,
        active=item.active,
        created_at=item.created_at,
        updated_at=item.updated_at,
        progress=compute_item_progress(db, item),
    )


def _next_item_number(db: Session, request_id: UUID) -> int:
    """Return the next per-Request item number (max + 1, never reused).

    Counts over all items (active and removed) so a removed item's number is
    never handed out again, keeping shared item URLs stable.
    """
    current_max = (
        db.query(func.max(models.RequestItem.item_number))
        .filter(models.RequestItem.request_id == request_id)
        .scalar()
    )
    return (current_max or 0) + 1


def _sanitize_item_centers(request: models.Request, ids: list[UUID]) -> list[UUID]:
    """Keep only ids that are among the Request's preferred centers, de-duped."""
    allowed = set(request.preferred_collection_center_ids)
    seen: set[UUID] = set()
    result: list[UUID] = []
    for cid in ids:
        if cid in allowed and cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def effective_item_center_ids(
    item: models.RequestItem, request: models.Request
) -> list[UUID]:
    """Resolve an item's drop-off centers against the Request's preferred list.

    Returns the item's own subset (filtered to the Request's *current* preferred
    centers); if that is empty, falls back to all of the Request's preferred
    centers, i.e. "all of them apply".
    """
    filtered = _sanitize_item_centers(request, item.preferred_collection_center_ids)
    return filtered or list(request.preferred_collection_center_ids)


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
    items = [_item_response(db, i, request) for i in list_active_items(db, request.id)]
    return schemas.RequestDetailResponse(
        **schemas.RequestResponse.model_validate(request).model_dump(),
        items=items,
    )


def build_item_detail(
    db: Session, request: models.Request, item: models.RequestItem
) -> schemas.RequestItemDetailResponse:
    """Serialize one item with Resource context + a last-activity timestamp."""
    from app.activity.constants import EntityType
    from app.activity.service import latest_activity_at
    from app.resources.service import get_or_raise as get_resource_or_raise

    resource = get_resource_or_raise(db, item.resource_id)
    base = _item_response(db, item, request)
    latest = latest_activity_at(
        db, entity_type=EntityType.REQUEST_ITEM, entity_id=item.id
    )
    last_activity = (
        max(item.updated_at, latest) if latest is not None else item.updated_at
    )
    return schemas.RequestItemDetailResponse(
        **base.model_dump(),
        resource_name=resource.name,
        resource_description=resource.description,
        resource_image_url=resource.image_url,
        resource_source_url=resource.source_url,
        request_title=request.title,
        request_status=request.status,
        last_activity_at=last_activity,
    )


# ---------------------------------------------------------------------------
# Derived help state + last activity (list view)
# ---------------------------------------------------------------------------


def compute_item_help_state(
    item: models.RequestItem, progress: schemas.RequestItemProgress
) -> HelpState:
    """Bucket one item by whether it still needs help (see ``HelpState``)."""
    if item.status in (RequestStatus.FULFILLED, RequestStatus.CLOSED):
        return HelpState.COMPLETED
    if item.quantity is not None and progress.committed_quantity >= item.quantity:
        return HelpState.COMMITTED
    return HelpState.NEEDS_HELP


def _help_state_from_items(db: Session, items: list[models.RequestItem]) -> HelpState:
    """Aggregate item help states into one campaign-level state."""
    if not items:
        return HelpState.NEEDS_HELP
    states = [compute_item_help_state(i, compute_item_progress(db, i)) for i in items]
    if any(s == HelpState.NEEDS_HELP for s in states):
        return HelpState.NEEDS_HELP
    if any(s == HelpState.COMMITTED for s in states):
        return HelpState.COMMITTED
    return HelpState.COMPLETED


def _request_last_activity(
    db: Session, request: models.Request, items: list[models.RequestItem]
) -> datetime:
    """Newest of the campaign's / items' updates and any activity rows."""
    from app.activity.models import ActivityLog

    ids = [request.id, *(i.id for i in items)]
    latest = (
        db.query(func.max(ActivityLog.created_at))
        .filter(ActivityLog.entity_id.in_(ids))
        .scalar()
    )
    candidates = [request.updated_at, *(i.updated_at for i in items)]
    if latest is not None:
        candidates.append(latest)
    return max(candidates)


def _request_countries(
    db: Session, request: models.Request, items: list[models.RequestItem]
) -> list[str]:
    """Distinct ISO country codes of the campaign's effective drop-off centers.

    Aggregates each active item's effective centers (its own subset, or the
    Request's preferred list as a fallback) and returns their distinct
    countries, sorted, so the directory can flag single-country campaigns.
    """
    center_ids: set[UUID] = set()
    for item in items:
        center_ids.update(effective_item_center_ids(item, request))
    return _countries_for_center_ids(db, list(center_ids))


def build_list_item(db: Session, request: models.Request) -> schemas.RequestListItem:
    """Serialize a campaign for the directory with help state + last activity."""
    items = list_active_items(db, request.id)
    return schemas.RequestListItem(
        **schemas.RequestResponse.model_validate(request).model_dump(),
        help_state=_help_state_from_items(db, items),
        last_activity_at=_request_last_activity(db, request, items),
        countries=_request_countries(db, request, items),
    )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def list_requests(
    db: Session,
    status: RequestStatus | None = None,
    viewer: User | None = None,
) -> list[models.Request]:
    """List Requests visible to ``viewer``.

    With an explicit ``status`` filter, returns only that status. With no
    filter, returns ``open`` **and** ``fulfilled`` campaigns so the directory
    can also surface completed ones (cancelled/``closed`` stay hidden).

    Unpublished campaigns are folded in for the people entitled to see them:
    a requester sees their own drafts/pending campaigns in the directory (so
    they can find and finish them) and maintainers see everyone's. To everyone
    else they do not exist.
    """
    query = db.query(models.Request).filter(models.Request.active.is_(True))
    if status is not None:
        query = query.filter(models.Request.status == status)
    else:
        query = query.filter(
            models.Request.status.in_([RequestStatus.OPEN, RequestStatus.FULFILLED])
        )
    requests = query.order_by(models.Request.created_at.desc()).all()
    # ``can_view_request`` short-circuits on the approved majority, so the
    # ownership lookup only runs for the handful of unpublished rows.
    return [r for r in requests if can_view_request(db, r, viewer)]


def list_review_queue(db: Session) -> list[models.Request]:
    """List campaigns awaiting review, oldest first (maintainer queue)."""
    return (
        db.query(models.Request)
        .filter(
            models.Request.active.is_(True),
            models.Request.moderation_status == ModerationStatus.PENDING,
        )
        .order_by(models.Request.submitted_at.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def create_request(
    db: Session, payload: schemas.RequestCreate, actor: User
) -> models.Request:
    """Create a Request, optionally with items (FR-038).

    Items are optional: the Request may start empty and have items added
    later (FR-122).

    New campaigns start as a **draft** and are published only once a maintainer
    approves them (FR-134). Maintainers/admins skip the queue — their campaigns
    are born approved, mirroring how the notices domain treats its own staff.
    """
    requester_user_id, requester_organization_id = assert_caller_can_own_on_behalf_of(
        db, actor, payload.owner_organization_id
    )
    self_publishes = has_global_override(actor)
    now = datetime.now(UTC)
    # Duplicate Resources are allowed: a need for the same part can recur, so a
    # Request may carry several items of one Resource, each tracked separately.
    for item in payload.items:
        _assert_resource_active(db, item.resource_id)

    request = models.Request(
        title=payload.title,
        description=payload.description,
        beneficiary=payload.beneficiary,
        packaging_instructions=payload.packaging_instructions,
        image_url=payload.image_url,
        image_focus_x=payload.image_focus_x,
        image_focus_y=payload.image_focus_y,
        deadline=payload.deadline,
        requester_user_id=requester_user_id,
        requester_organization_id=requester_organization_id,
        created_by_id=actor.id,
        preferred_collection_center_ids=payload.preferred_collection_center_ids,
        moderation_status=(
            ModerationStatus.APPROVED if self_publishes else ModerationStatus.DRAFT
        ),
        submitted_at=now if self_publishes else None,
        reviewed_by_id=actor.id if self_publishes else None,
        reviewed_at=now if self_publishes else None,
    )
    db.add(request)
    db.flush()
    # New Request, so items are numbered 1..N in the order given.
    for number, item in enumerate(payload.items, start=1):
        db.add(
            models.RequestItem(
                request_id=request.id,
                item_number=number,
                resource_id=item.resource_id,
                quantity=item.quantity,
                unit=item.unit,
                preferred_collection_center_ids=_sanitize_item_centers(
                    request, item.preferred_collection_center_ids
                ),
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


def reopen_request(db: Session, request_id: UUID, actor: User) -> models.Request:
    """Reopen a closed/fulfilled Request (undo an accidental close).

    Clears the campaign's closed state and reopens the items that were closed
    by *this* close (``closed_reason == REQUEST_CLOSED``), so items the
    requester had closed on purpose stay closed. Contributions that were
    released on close are terminal and are not restored; the reopened items
    simply accept new commitments again.
    """
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    if request.status == RequestStatus.OPEN:
        raise RequestNotClosedExceptionError

    for item in list_active_items(db, request.id):
        if (
            item.status != RequestStatus.OPEN
            and item.closed_reason == ClosedReason.REQUEST_CLOSED
        ):
            item.status = RequestStatus.OPEN
            item.closed_at = None
            item.closed_by_id = None
            item.closed_reason = None

    request.status = RequestStatus.OPEN
    request.closed_at = None
    request.closed_by_id = None
    request.closed_reason = None
    write_audit(
        db, actor.id, AuditAction.REOPEN_REQUEST, AuditTargetType.REQUEST, request.id
    )
    db.commit()
    db.refresh(request)
    return request


# ---------------------------------------------------------------------------
# Moderation (FR-134): draft -> pending -> approved | changes_requested |
# rejected. Sent-back and rejected campaigns may be fixed and resubmitted.
# ---------------------------------------------------------------------------


def _notify_moderators(db: Session, request: models.Request, actor: User) -> None:
    """Ping every maintainer/admin that a campaign is waiting for review."""
    from app.notifications.constants import REQUEST_SUBMITTED_EVENT
    from app.notifications.service import fan_out_to_users, maintainer_user_ids

    fan_out_to_users(
        db,
        recipient_ids=maintainer_user_ids(db),
        entity_type=EntityType.REQUEST,
        entity_id=request.id,
        actor_user_id=actor.id,
        event=REQUEST_SUBMITTED_EVENT,
    )


def _notify_requesters(db: Session, request: models.Request, actor: User) -> None:
    """Tell the campaign's requesters that a maintainer has reviewed it."""
    from app.notifications.constants import REQUEST_REVIEWED_EVENT
    from app.notifications.service import fan_out_to_users

    fan_out_to_users(
        db,
        recipient_ids=effective_requester_user_ids(db, request),
        entity_type=EntityType.REQUEST,
        entity_id=request.id,
        actor_user_id=actor.id,
        event=REQUEST_REVIEWED_EVENT,
    )


def submit_for_review(db: Session, request_id: UUID, actor: User) -> models.Request:
    """Send a draft (or sent-back / rejected) campaign to the review queue.

    Requires at least one item (FR-119): an empty campaign gives a maintainer
    nothing to review. Clears any previous review note so the author is not
    left staring at stale feedback while they wait.
    """
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    if request.moderation_status not in SUBMITTABLE_STATUSES:
        raise RequestNotSubmittableExceptionError
    if not list_active_items(db, request.id):
        raise RequestNeedsItemExceptionError

    request.moderation_status = ModerationStatus.PENDING
    request.submitted_at = datetime.now(UTC)
    request.review_note = None
    request.reviewed_by_id = None
    request.reviewed_at = None
    write_audit(
        db, actor.id, AuditAction.SUBMIT_REQUEST, AuditTargetType.REQUEST, request.id
    )
    _notify_moderators(db, request, actor)
    db.commit()
    db.refresh(request)
    return request


def _review(
    db: Session,
    request_id: UUID,
    actor: User,
    *,
    outcome: ModerationStatus,
    action: AuditAction,
    note: str | None,
) -> models.Request:
    """Apply a maintainer's verdict to a campaign awaiting review.

    The caller (router) has already gated on maintainer/admin. Only a campaign
    that is actually ``pending`` can be reviewed, so two maintainers acting on
    the same queue entry cannot both "decide" it.
    """
    request = get_request_or_raise(db, request_id)
    if request.moderation_status != ModerationStatus.PENDING:
        raise RequestNotPendingExceptionError

    request.moderation_status = outcome
    # An approval clears the note; a send-back/rejection carries the reason.
    request.review_note = None if outcome == ModerationStatus.APPROVED else note
    request.reviewed_by_id = actor.id
    request.reviewed_at = datetime.now(UTC)
    write_audit(
        db,
        actor.id,
        action,
        AuditTargetType.REQUEST,
        request.id,
        reason=note,
    )
    _notify_requesters(db, request, actor)
    db.commit()
    db.refresh(request)
    return request


def approve_request(db: Session, request_id: UUID, actor: User) -> models.Request:
    """Publish a campaign awaiting review (maintainer/admin)."""
    return _review(
        db,
        request_id,
        actor,
        outcome=ModerationStatus.APPROVED,
        action=AuditAction.APPROVE_REQUEST,
        note=None,
    )


def request_changes(
    db: Session, request_id: UUID, note: str, actor: User
) -> models.Request:
    """Send a campaign back to its author asking for more information."""
    return _review(
        db,
        request_id,
        actor,
        outcome=ModerationStatus.CHANGES_REQUESTED,
        action=AuditAction.REQUEST_CHANGES_REQUEST,
        note=note,
    )


def reject_request(
    db: Session, request_id: UUID, note: str | None, actor: User
) -> models.Request:
    """Turn a campaign down. It is never published, but may be fixed + resent."""
    return _review(
        db,
        request_id,
        actor,
        outcome=ModerationStatus.REJECTED,
        action=AuditAction.REJECT_REQUEST,
        note=note,
    )


def unpublish_request(
    db: Session, request_id: UUID, note: str | None, actor: User
) -> models.Request:
    """Pull a published campaign back into the review queue (FR-135).

    The takedown lever: a maintainer/admin who spots something wrong with a
    live campaign can hide it immediately — it drops out of every public read
    the moment this commits, because ``can_view_request`` gates on
    ``approved``. It lands back in the queue as ``pending`` (rather than being
    deleted) so it can be fixed and re-approved instead of lost.

    Effective requesters may also pull their own campaign back — the same
    "take it down now, sort it out after" escape hatch, without needing a
    maintainer to be awake.
    """
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    if request.moderation_status != ModerationStatus.APPROVED:
        raise RequestNotApprovedExceptionError

    request.moderation_status = ModerationStatus.PENDING
    request.review_note = note
    request.submitted_at = datetime.now(UTC)
    request.reviewed_by_id = actor.id
    request.reviewed_at = datetime.now(UTC)
    write_audit(
        db,
        actor.id,
        AuditAction.UNPUBLISH_REQUEST,
        AuditTargetType.REQUEST,
        request.id,
        reason=note,
    )
    # Tell the queue it has work, and the author their campaign went dark.
    _notify_moderators(db, request, actor)
    _notify_requesters(db, request, actor)
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
    _assert_resource_active(db, payload.resource_id)

    item = models.RequestItem(
        request_id=request.id,
        item_number=_next_item_number(db, request.id),
        resource_id=payload.resource_id,
        quantity=payload.quantity,
        unit=payload.unit,
        preferred_collection_center_ids=_sanitize_item_centers(
            request, payload.preferred_collection_center_ids
        ),
        description=payload.description,
        deadline=payload.deadline,
    )
    db.add(item)
    db.flush()
    _record_item_added(db, request, item, actor)
    db.commit()
    db.refresh(item)
    return _item_response(db, item, request)


def _record_item_added(
    db: Session,
    request: models.Request,
    item: models.RequestItem,
    actor: User,
) -> None:
    """Log an ``item_added`` event on the Request so its watchers get pinged.

    Recorded on the Request (not the new item, which has no watchers yet), so
    people watching the campaign are notified when a new need is added (FR-122).
    Function-local imports keep the activity domain out of the import cycle.
    """
    from app.activity.constants import ActivityAction, EntityType
    from app.activity.service import record
    from app.resources.service import get_or_raise as get_resource_or_raise

    resource = get_resource_or_raise(db, item.resource_id)
    record(
        db,
        entity_type=EntityType.REQUEST,
        entity_id=request.id,
        actor_user_id=actor.id,
        action=ActivityAction.ITEM_ADDED,
        changes={
            "item_number": item.item_number,
            "resource_name": resource.name,
        },
        # Deep-link the watch notification to (and highlight) the new item's
        # card on the request page, mirroring the comment/tracking anchors.
        anchor=f"item-{item.id}",
    )


def _get_item_in_request(
    db: Session, request_id: UUID, item_id: UUID
) -> models.RequestItem:
    item = get_item_or_raise(db, item_id)
    if item.request_id != request_id:
        raise ItemRequestMismatchExceptionError
    return item


def _get_item_by_number(
    db: Session, request_id: UUID, item_number: int
) -> models.RequestItem:
    """Return the item with the given per-Request number, or raise 404."""
    get_request_or_raise(db, request_id)
    item = (
        db.query(models.RequestItem)
        .filter(
            models.RequestItem.request_id == request_id,
            models.RequestItem.item_number == item_number,
        )
        .first()
    )
    if item is None:
        raise RequestItemNotFoundExceptionError(item_number)
    return item


def get_item_detail(
    db: Session, request_id: UUID, item_number: int, viewer: User | None = None
) -> schemas.RequestItemDetailResponse:
    """Fetch one item by its per-Request number for its public page."""
    request = get_request_or_raise(db, request_id)
    assert_can_view_request(db, request, viewer)
    item = _get_item_by_number(db, request_id, item_number)
    return build_item_detail(db, request, item)


def list_item_commitments(
    db: Session, request_id: UUID, item_number: int, viewer: User | None = None
) -> list["ItemCommitmentResponse"]:
    """List the public commitments on an item, addressed by its number."""
    from app.contributions.service import list_public_for_item

    request = get_request_or_raise(db, request_id)
    assert_can_view_request(db, request, viewer)
    item = _get_item_by_number(db, request_id, item_number)
    return list_public_for_item(db, item.id)


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

    data = payload.model_dump(exclude_unset=True)
    # A per-item center subset is constrained to the Request's preferred list.
    if "preferred_collection_center_ids" in data:
        data["preferred_collection_center_ids"] = _sanitize_item_centers(
            request, data["preferred_collection_center_ids"]
        )
    for field, value in data.items():
        setattr(item, field, value)
    db.flush()
    # A new target may now be met (or not) — re-evaluate fulfillment.
    recompute_item_fulfillment(db, item)
    db.commit()
    db.refresh(item)
    return _item_response(db, item, request)


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
    return _item_response(db, item, request)


def reopen_item(
    db: Session, request_id: UUID, item_id: UUID, actor: User
) -> schemas.RequestItemResponse:
    """Reopen a single closed/fulfilled item on an open Request (undo a close).

    The parent Request must be open; if the whole campaign is closed, reopen
    it instead. Only the item's closed state is cleared — its progress is
    unchanged, so an over-committed item simply reads as "committed" again.
    """
    request = get_request_or_raise(db, request_id)
    _assert_effective_requester(db, request, actor)
    _assert_open(request)
    item = _get_item_in_request(db, request_id, item_id)
    if item.status == RequestStatus.OPEN:
        raise RequestItemNotClosedExceptionError
    item.status = RequestStatus.OPEN
    item.closed_at = None
    item.closed_by_id = None
    item.closed_reason = None
    db.commit()
    db.refresh(item)
    return _item_response(db, item, request)


def _item_has_active_contributions(db: Session, item_id: UUID) -> bool:
    from app.contributions.constants import ContributionStatus
    from app.contributions.models import Contribution

    active_states = (
        ContributionStatus.CLAIMED,
        ContributionStatus.PREPARED,
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


def close_open_items_for_resource(db: Session, resource_id: UUID, actor: User) -> None:
    """Close all open items referencing a Resource being force-archived (FR-077)."""
    items = (
        db.query(models.RequestItem)
        .filter(
            models.RequestItem.resource_id == resource_id,
            models.RequestItem.active.is_(True),
            models.RequestItem.status == RequestStatus.OPEN,
        )
        .all()
    )
    touched_request_ids: set[UUID] = set()
    for item in items:
        _close_item(db, item, ClosedReason.RESOURCE_ARCHIVED, actor)
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
