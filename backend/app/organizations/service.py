"""Organization business logic: CRUD, verification, and membership."""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.collection_centers.models import CollectionCenter
from app.handles import (
    RESERVED_HANDLES,
    is_handle_taken,
    slugify_handle,
    unique_org_handle,
    validate_handle,
)
from app.permissions import active_org_owner_user_ids, has_global_override
from app.users.exceptions import UserNotFoundExceptionError
from app.users.models import User

from . import models, schemas
from .constants import OrganizationRole, OrganizationStatus
from .exceptions import (
    NotEffectiveOwnerExceptionError,
    NotOrgMemberExceptionError,
    OrganizationNotFoundExceptionError,
    OrgArchiveBlockedExceptionError,
    OrgHandleTakenExceptionError,
    OrgNameTakenExceptionError,
    OwnerCannotLeaveExceptionError,
)


def get_or_raise(db: Session, organization_id: UUID) -> models.Organization:
    """Return an organization by id or raise ``OrganizationNotFound``."""
    org = (
        db.query(models.Organization)
        .filter(models.Organization.id == organization_id)
        .first()
    )
    if org is None:
        raise OrganizationNotFoundExceptionError(organization_id)
    return org


def _active_membership(
    db: Session, organization_id: UUID, user_id: UUID
) -> models.OrganizationMembership | None:
    return (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.user_id == user_id,
            models.OrganizationMembership.active.is_(True),
        )
        .first()
    )


def is_active_member(db: Session, organization_id: UUID, user_id: UUID) -> bool:
    """Return True if the user is an active member of the organization."""
    return _active_membership(db, organization_id, user_id) is not None


def _assert_owner_or_override(
    db: Session, org: models.Organization, actor: User
) -> None:
    """Require the actor to be an org owner or a maintainer/admin."""
    if has_global_override(actor):
        return
    if actor.id not in active_org_owner_user_ids(db, org.id):
        raise NotEffectiveOwnerExceptionError


def can_view_unverified(db: Session, org: models.Organization, viewer: User) -> bool:
    """Return True if the viewer may see an unverified organization (FR-105)."""
    if has_global_override(viewer):
        return True
    return is_active_member(db, org.id, viewer.id)


def list_organizations(
    db: Session,
    viewer: User | None,
    country: str | None = None,
    q: str | None = None,
    verified: bool | None = None,
) -> list[models.Organization]:
    """List organizations visible to the viewer (public read, FR-105).

    Guests and regular users see only verified, active organizations.
    Maintainers/admins may pass ``verified`` to override the default and
    list unverified ones too.
    """
    query = db.query(models.Organization).filter(models.Organization.active.is_(True))

    is_privileged = viewer is not None and has_global_override(viewer)
    if is_privileged and verified is not None:
        query = query.filter(models.Organization.verified.is_(verified))
    elif not is_privileged:
        query = query.filter(models.Organization.verified.is_(True))

    if country is not None:
        query = query.filter(models.Organization.country == country)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                models.Organization.name.ilike(pattern),
                models.Organization.description.ilike(pattern),
            )
        )
    return query.order_by(models.Organization.name.asc()).all()


def create_organization(
    db: Session, payload: schemas.OrganizationCreate, actor: User
) -> models.Organization:
    """Create an organization; the actor becomes its owner (FR-095).

    The public URL handle is derived from the name (``slugify_handle``) and
    must be unique across the shared user+org namespace. A collision (e.g.
    "Cruz Roja" after "cruz roja" already exists — both slug to
    ``cruz-roja``) is rejected so the likely duplicate surfaces.
    """
    existing = (
        db.query(models.Organization)
        .filter(models.Organization.name == payload.name)
        .first()
    )
    if existing is not None:
        raise OrgNameTakenExceptionError(payload.name)

    handle = slugify_handle(payload.name)
    # A collision with an existing user/org is a likely duplicate — reject so
    # it surfaces. A collision with a reserved route word is not the caller's
    # fault (the handle is auto-derived), so quietly suffix past it instead.
    if is_handle_taken(db, handle):
        raise OrgNameTakenExceptionError(payload.name)
    if handle in RESERVED_HANDLES:
        handle = unique_org_handle(db, payload.name)

    org = models.Organization(
        name=payload.name,
        handle=handle,
        description=payload.description,
        contact=payload.contact,
        website=payload.website,
        country=payload.country,
        registered_by_id=actor.id,
    )
    db.add(org)
    db.flush()

    db.add(
        models.OrganizationMembership(
            organization_id=org.id,
            user_id=actor.id,
            role=OrganizationRole.OWNER,
            invited_by_id=actor.id,
        )
    )
    db.commit()
    db.refresh(org)
    return org


def update_organization(
    db: Session,
    organization_id: UUID,
    payload: schemas.OrganizationUpdate,
    actor: User,
) -> models.Organization:
    """Edit an organization (owner / maintainer / admin)."""
    org = get_or_raise(db, organization_id)
    _assert_owner_or_override(db, org, actor)

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != org.name:
        clash = (
            db.query(models.Organization)
            .filter(
                models.Organization.name == data["name"],
                models.Organization.id != org.id,
            )
            .first()
        )
        if clash is not None:
            raise OrgNameTakenExceptionError(data["name"])
    if "handle" in data and data["handle"] is not None:
        new_handle = validate_handle(
            data["handle"], error_code="INVALID_ORG_HANDLE"
        ).lower()
        if new_handle != org.handle and is_handle_taken(
            db, new_handle, exclude_org_id=org.id
        ):
            raise OrgHandleTakenExceptionError(new_handle)
        data["handle"] = new_handle
    for field, value in data.items():
        setattr(org, field, value)

    db.commit()
    db.refresh(org)
    return org


def verify_organization(
    db: Session, organization_id: UUID, actor: User
) -> models.Organization:
    """Flip ``verified=true`` (maintainer/admin, FR-096)."""
    org = get_or_raise(db, organization_id)
    org.verified = True
    org.verified_by_id = actor.id
    write_audit(
        db,
        actor.id,
        AuditAction.VERIFY_ORGANIZATION,
        AuditTargetType.ORGANIZATION,
        org.id,
    )
    db.commit()
    db.refresh(org)
    return org


def revoke_verification(
    db: Session, organization_id: UUID, reason: str | None, actor: User
) -> models.Organization:
    """Revoke verification (maintainer/admin)."""
    org = get_or_raise(db, organization_id)
    org.verified = False
    org.verified_by_id = None
    write_audit(
        db,
        actor.id,
        AuditAction.REVOKE_ORGANIZATION_VERIFICATION,
        AuditTargetType.ORGANIZATION,
        org.id,
        reason=reason,
    )
    db.commit()
    db.refresh(org)
    return org


def archive_organization(
    db: Session, organization_id: UUID, actor: User
) -> models.Organization:
    """Soft-archive an organization (owner / maintainer / admin, FR-104).

    Rejected if the org still owns any active Collection Center. (Resources
    are added in Phase 4 and will extend this guard.)
    """
    org = get_or_raise(db, organization_id)
    _assert_owner_or_override(db, org, actor)

    active_cc_count = (
        db.query(CollectionCenter)
        .filter(
            CollectionCenter.owner_organization_id == org.id,
            CollectionCenter.active.is_(True),
        )
        .count()
    )
    if active_cc_count > 0:
        raise OrgArchiveBlockedExceptionError(active_cc_count)

    org.active = False
    org.status = OrganizationStatus.INACTIVE
    db.commit()
    db.refresh(org)
    return org


def list_members(
    db: Session, organization_id: UUID
) -> list[schemas.MembershipResponse]:
    """List active members of an organization with their usernames."""
    get_or_raise(db, organization_id)
    rows = (
        db.query(models.OrganizationMembership, User)
        .join(User, User.id == models.OrganizationMembership.user_id)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.active.is_(True),
        )
        .order_by(models.OrganizationMembership.created_at.asc())
        .all()
    )
    return [_membership_response(m, u) for m, u in rows]


def _membership_response(
    membership: models.OrganizationMembership, user: User
) -> schemas.MembershipResponse:
    return schemas.MembershipResponse(
        id=membership.id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        username=user.username,
        user_role=user.role,
        role=membership.role,
        active=membership.active,
        created_at=membership.created_at,
    )


def add_member(
    db: Session, organization_id: UUID, username: str, actor: User
) -> schemas.MembershipResponse:
    """Add an existing user as a member (owner only, FR-098)."""
    org = get_or_raise(db, organization_id)
    _assert_owner_or_override(db, org, actor)

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise UserNotFoundExceptionError(username)

    membership = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == org.id,
            models.OrganizationMembership.user_id == user.id,
        )
        .order_by(models.OrganizationMembership.created_at.desc())
        .first()
    )
    if membership is not None and membership.active:
        return _membership_response(membership, user)
    if membership is not None:
        membership.active = True
        membership.role = OrganizationRole.MEMBER
        membership.invited_by_id = actor.id
    else:
        membership = models.OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role=OrganizationRole.MEMBER,
            invited_by_id=actor.id,
        )
        db.add(membership)

    write_audit(
        db,
        actor.id,
        AuditAction.ORG_ADD_MEMBER,
        AuditTargetType.ORGANIZATION_MEMBERSHIP,
        org.id,
        reason=f"user={user.username}",
    )
    db.commit()
    db.refresh(membership)
    return _membership_response(membership, user)


def remove_member(
    db: Session, organization_id: UUID, target_user_id: UUID, actor: User
) -> None:
    """Remove a member (owner removes others; member removes self).

    Owners cannot self-remove without first transferring ownership
    (FR-100).
    """
    org = get_or_raise(db, organization_id)
    is_self = actor.id == target_user_id
    if not is_self:
        _assert_owner_or_override(db, org, actor)

    membership = _active_membership(db, org.id, target_user_id)
    if membership is None:
        raise NotOrgMemberExceptionError
    if membership.role == OrganizationRole.OWNER:
        raise OwnerCannotLeaveExceptionError

    membership.active = False
    write_audit(
        db,
        actor.id,
        AuditAction.ORG_REMOVE_MEMBER,
        AuditTargetType.ORGANIZATION_MEMBERSHIP,
        org.id,
        reason=f"user_id={target_user_id}",
    )
    db.commit()


def transfer_ownership(
    db: Session, organization_id: UUID, target_user_id: UUID, actor: User
) -> models.Organization:
    """Atomically hand ownership to an existing member (owner, FR-101)."""
    org = get_or_raise(db, organization_id)
    _assert_owner_or_override(db, org, actor)

    target = _active_membership(db, org.id, target_user_id)
    if target is None:
        raise NotOrgMemberExceptionError
    if target.role == OrganizationRole.OWNER:
        return org

    _swap_owner(db, org, target)
    write_audit(
        db,
        actor.id,
        AuditAction.ORG_TRANSFER_OWNERSHIP,
        AuditTargetType.ORGANIZATION,
        org.id,
        reason=f"target_user_id={target_user_id}",
    )
    db.commit()
    db.refresh(org)
    return org


def force_transfer_ownership(
    db: Session, organization_id: UUID, target_user_id: UUID, actor: User
) -> models.Organization:
    """Maintainer/admin rescue: assign ownership to any user (FR-102)."""
    org = get_or_raise(db, organization_id)

    target_user = db.query(User).filter(User.id == target_user_id).first()
    if target_user is None:
        raise UserNotFoundExceptionError(target_user_id)

    target = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == org.id,
            models.OrganizationMembership.user_id == target_user_id,
            models.OrganizationMembership.active.is_(True),
        )
        .first()
    )
    if target is None:
        target = models.OrganizationMembership(
            organization_id=org.id,
            user_id=target_user_id,
            role=OrganizationRole.MEMBER,
            invited_by_id=actor.id,
        )
        db.add(target)
        db.flush()

    _swap_owner(db, org, target)
    write_audit(
        db,
        actor.id,
        AuditAction.FORCE_TRANSFER_ORG_OWNERSHIP,
        AuditTargetType.ORGANIZATION,
        org.id,
        reason=f"target_user_id={target_user_id}",
    )
    db.commit()
    db.refresh(org)
    return org


def _swap_owner(
    db: Session, org: models.Organization, target: models.OrganizationMembership
) -> None:
    """Demote existing active owners to member, then promote ``target``.

    The demotion is flushed before the promotion so the
    ``uniq_org_owner_active`` partial index never sees two owners.
    """
    current_owners = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == org.id,
            models.OrganizationMembership.role == OrganizationRole.OWNER,
            models.OrganizationMembership.active.is_(True),
        )
        .all()
    )
    for owner in current_owners:
        owner.role = OrganizationRole.MEMBER
    db.flush()
    target.role = OrganizationRole.OWNER
    db.flush()
