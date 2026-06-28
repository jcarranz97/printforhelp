"""Collection Center business logic: CRUD, verification, contributors."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.permissions import (
    assert_caller_can_own_on_behalf_of,
    effective_cc_member_user_ids,
    effective_owner_user_ids,
    has_global_override,
)
from app.users.exceptions import UserNotFoundExceptionError
from app.users.models import User

from . import models, schemas
from .constants import CollectionCenterRole, CollectionCenterStatus
from .exceptions import (
    CCArchiveBlockedExceptionError,
    CollectionCenterNotFoundExceptionError,
    NotContributorExceptionError,
    NotEffectiveMemberExceptionError,
    NotEffectiveOwnerExceptionError,
)


def get_or_raise(db: Session, collection_center_id: UUID) -> models.CollectionCenter:
    """Return a collection center by id or raise ``NotFound``."""
    cc = (
        db.query(models.CollectionCenter)
        .filter(models.CollectionCenter.id == collection_center_id)
        .first()
    )
    if cc is None:
        raise CollectionCenterNotFoundExceptionError(collection_center_id)
    return cc


def is_effective_owner(db: Session, cc: models.CollectionCenter, user: User) -> bool:
    """Return True if the user has owner powers on the center (or override)."""
    return has_global_override(user) or user.id in effective_owner_user_ids(db, cc)


def is_effective_member(db: Session, cc: models.CollectionCenter, user: User) -> bool:
    """Return True if the user has member powers on the center (or override)."""
    return has_global_override(user) or user.id in effective_cc_member_user_ids(
        db, cc.id, cc
    )


def _assert_effective_owner(
    db: Session, cc: models.CollectionCenter, user: User
) -> None:
    if not is_effective_owner(db, cc, user):
        raise NotEffectiveOwnerExceptionError


def _assert_effective_member(
    db: Session, cc: models.CollectionCenter, user: User
) -> None:
    if not is_effective_member(db, cc, user):
        raise NotEffectiveMemberExceptionError


def list_collection_centers(
    db: Session,
    viewer: User | None,
    country: str | None = None,
    city: str | None = None,
    verified: bool | None = None,
) -> list[models.CollectionCenter]:
    """List collection centers (public read, FR-072).

    Everyone — guests included — sees all operational (``status=active``)
    centers, whether or not they are verified; the ``verified`` flag on
    each row drives the "No verificado" badge in the UI. The ``verified``
    query filter is available to **everyone** (e.g. a third-party app
    pulling only verified centers, or a maintainer's unverified queue).
    The only extra privilege maintainers/admins get is seeing
    operationally-inactive centers too.
    """
    query = db.query(models.CollectionCenter).filter(
        models.CollectionCenter.active.is_(True)
    )
    if country is not None:
        query = query.filter(models.CollectionCenter.country == country)
    if city is not None:
        query = query.filter(models.CollectionCenter.city == city)

    # Non-privileged callers only ever see operational centers; maintainers
    # and admins additionally see operationally-inactive ones.
    if viewer is None or not has_global_override(viewer):
        query = query.filter(
            models.CollectionCenter.status == CollectionCenterStatus.ACTIVE
        )

    # The verified filter applies to every caller.
    if verified is not None:
        query = query.filter(models.CollectionCenter.verified.is_(verified))

    return query.order_by(models.CollectionCenter.name.asc()).all()


def create_collection_center(
    db: Session,
    payload: schemas.CollectionCenterCreate,
    actor: User,
    *,
    on_behalf_of_org_allowed: bool = True,
) -> models.CollectionCenter:
    """Create a center; owner defaults to the caller (FR-083).

    For anonymous submissions the caller is the system ``anonymous`` user
    and ``on_behalf_of_org_allowed`` is False, so the center always
    self-owns and any ``owner_organization_id`` in the payload is ignored.
    """
    org_id = payload.owner_organization_id if on_behalf_of_org_allowed else None
    owner_user_id, owner_organization_id = assert_caller_can_own_on_behalf_of(
        db, actor, org_id
    )
    cc = models.CollectionCenter(
        name=payload.name,
        address=payload.address,
        country=payload.country,
        city=payload.city,
        contact=payload.contact,
        opening_hours=payload.opening_hours,
        notes=payload.notes,
        registered_by_id=actor.id,
        owner_user_id=owner_user_id,
        owner_organization_id=owner_organization_id,
    )
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc


def update_collection_center(
    db: Session,
    collection_center_id: UUID,
    payload: schemas.CollectionCenterUpdate,
    actor: User,
) -> models.CollectionCenter:
    """Edit a center (effective member or mod/admin, FR-031)."""
    cc = get_or_raise(db, collection_center_id)
    _assert_effective_member(db, cc, actor)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cc, field, value)
    db.commit()
    db.refresh(cc)
    return cc


def verify_collection_center(
    db: Session, collection_center_id: UUID, actor: User
) -> models.CollectionCenter:
    """Verify a center (maintainer/admin, FR-027)."""
    cc = get_or_raise(db, collection_center_id)
    cc.verified = True
    cc.verified_by_id = actor.id
    write_audit(
        db,
        actor.id,
        AuditAction.VERIFY_COLLECTION_CENTER,
        AuditTargetType.COLLECTION_CENTER,
        cc.id,
    )
    db.commit()
    db.refresh(cc)
    return cc


def revoke_verification(
    db: Session, collection_center_id: UUID, reason: str | None, actor: User
) -> models.CollectionCenter:
    """Revoke a center's verification (maintainer/admin)."""
    cc = get_or_raise(db, collection_center_id)
    cc.verified = False
    cc.verified_by_id = None
    write_audit(
        db,
        actor.id,
        AuditAction.REVOKE_COLLECTION_CENTER,
        AuditTargetType.COLLECTION_CENTER,
        cc.id,
        reason=reason,
    )
    db.commit()
    db.refresh(cc)
    return cc


def toggle_status(
    db: Session,
    collection_center_id: UUID,
    status: CollectionCenterStatus,
    actor: User,
) -> models.CollectionCenter:
    """Set a center's operational status (effective member, FR-078)."""
    cc = get_or_raise(db, collection_center_id)
    _assert_effective_member(db, cc, actor)
    cc.status = status
    db.commit()
    db.refresh(cc)
    return cc


def archive_collection_center(
    db: Session, collection_center_id: UUID, actor: User
) -> models.CollectionCenter:
    """Owner-side archive (effective owner, FR-079).

    Rejected if open Contributions are routed to the center. Contributions
    land in Phase 4; the guard is a no-op until then.
    """
    cc = get_or_raise(db, collection_center_id)
    _assert_effective_owner(db, cc, actor)

    # The contributions domain lands in Phase 4. Once it exists, count
    # active Contributions in non-terminal states routed to this center and
    # raise CCArchiveBlockedExceptionError when any remain. Until then there
    # are no Contributions, so the guard passes unconditionally.
    open_contributions = 0
    if open_contributions > 0:  # pragma: no cover - Phase 4 guard
        raise CCArchiveBlockedExceptionError(open_contributions)

    cc.active = False
    cc.status = CollectionCenterStatus.INACTIVE
    db.commit()
    db.refresh(cc)
    return cc


def force_archive_collection_center(
    db: Session, collection_center_id: UUID, actor: User
) -> models.CollectionCenter:
    """Maintainer/admin force-archive (FR-080).

    Auto-releases routed Contributions. Contributions land in Phase 4;
    until then there is nothing to release.
    """
    cc = get_or_raise(db, collection_center_id)
    cc.active = False
    cc.status = CollectionCenterStatus.INACTIVE
    write_audit(
        db,
        actor.id,
        AuditAction.FORCE_ARCHIVE_COLLECTION_CENTER,
        AuditTargetType.COLLECTION_CENTER,
        cc.id,
    )
    db.commit()
    db.refresh(cc)
    return cc


def list_contributors(
    db: Session, collection_center_id: UUID
) -> list[schemas.ContributorResponse]:
    """List active per-center contributors with their usernames."""
    get_or_raise(db, collection_center_id)
    rows = (
        db.query(models.CollectionCenterMembership, User)
        .join(User, User.id == models.CollectionCenterMembership.user_id)
        .filter(
            models.CollectionCenterMembership.collection_center_id
            == collection_center_id,
            models.CollectionCenterMembership.active.is_(True),
        )
        .order_by(models.CollectionCenterMembership.created_at.asc())
        .all()
    )
    return [_contributor_response(m, u) for m, u in rows]


def _contributor_response(
    membership: models.CollectionCenterMembership, user: User
) -> schemas.ContributorResponse:
    return schemas.ContributorResponse(
        id=membership.id,
        collection_center_id=membership.collection_center_id,
        user_id=membership.user_id,
        username=user.username,
        user_role=user.role,
        role=membership.role,
        active=membership.active,
        created_at=membership.created_at,
    )


def add_contributor(
    db: Session, collection_center_id: UUID, username: str, actor: User
) -> schemas.ContributorResponse:
    """Add a per-center contributor (effective owner, FR-084)."""
    cc = get_or_raise(db, collection_center_id)
    _assert_effective_owner(db, cc, actor)

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise UserNotFoundExceptionError(username)

    membership = (
        db.query(models.CollectionCenterMembership)
        .filter(
            models.CollectionCenterMembership.collection_center_id == cc.id,
            models.CollectionCenterMembership.user_id == user.id,
        )
        .order_by(models.CollectionCenterMembership.created_at.desc())
        .first()
    )
    if membership is not None and membership.active:
        return _contributor_response(membership, user)
    if membership is not None:
        membership.active = True
        membership.role = CollectionCenterRole.CONTRIBUTOR
        membership.invited_by_id = actor.id
    else:
        membership = models.CollectionCenterMembership(
            collection_center_id=cc.id,
            user_id=user.id,
            role=CollectionCenterRole.CONTRIBUTOR,
            invited_by_id=actor.id,
        )
        db.add(membership)

    write_audit(
        db,
        actor.id,
        AuditAction.ADD_CONTRIBUTOR,
        AuditTargetType.COLLECTION_CENTER_MEMBERSHIP,
        cc.id,
        reason=f"user={user.username}",
    )
    db.commit()
    db.refresh(membership)
    return _contributor_response(membership, user)


def remove_contributor(
    db: Session, collection_center_id: UUID, target_user_id: UUID, actor: User
) -> None:
    """Remove a contributor (effective owner removes; contributor self-removes)."""
    cc = get_or_raise(db, collection_center_id)
    is_self = actor.id == target_user_id
    if not is_self:
        _assert_effective_owner(db, cc, actor)

    membership = (
        db.query(models.CollectionCenterMembership)
        .filter(
            models.CollectionCenterMembership.collection_center_id == cc.id,
            models.CollectionCenterMembership.user_id == target_user_id,
            models.CollectionCenterMembership.active.is_(True),
        )
        .first()
    )
    if membership is None:
        raise NotContributorExceptionError

    membership.active = False
    write_audit(
        db,
        actor.id,
        AuditAction.REMOVE_CONTRIBUTOR,
        AuditTargetType.COLLECTION_CENTER_MEMBERSHIP,
        cc.id,
        reason=f"user_id={target_user_id}",
    )
    db.commit()
