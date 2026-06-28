"""Shared authorization helpers.

These codify the polymorphic owner / member model documented in
``docs/architecture/database-schema.md``. Service code never branches on
which owner FK is set; it asks these helpers for the set of users that
hold owner- or member-equivalent powers on an asset, then checks
membership (or a global maintainer/admin override) against that set.
"""

import uuid

from sqlalchemy.orm import Session

from app.collection_centers.models import (
    CollectionCenter,
    CollectionCenterMembership,
)
from app.organizations.constants import OrganizationRole
from app.organizations.exceptions import OrgMembershipRequiredExceptionError
from app.organizations.models import OrganizationMembership
from app.parts.models import Part
from app.requests.models import Request
from app.users.constants import UserRole
from app.users.models import User

# Assets with the two-nullable-FK polymorphic owner (FR-107): Collection
# Centers and Parts. Requests carry the same shape under the ``requester_*``
# field names and are handled by ``effective_requester_user_ids`` below.
PolymorphicOwnable = CollectionCenter | Part


def has_global_override(user: User) -> bool:
    """Return True if the user is a maintainer or admin (NFR-006)."""
    return user.role in (UserRole.MAINTAINER, UserRole.ADMIN)


def active_org_owner_user_ids(
    db: Session, organization_id: uuid.UUID
) -> set[uuid.UUID]:
    """Return the active ``owner`` members of an organization (FR-100)."""
    rows = (
        db.query(OrganizationMembership.user_id)
        .filter(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == OrganizationRole.OWNER,
            OrganizationMembership.active.is_(True),
        )
        .all()
    )
    return {row.user_id for row in rows}


def active_org_member_user_ids(
    db: Session, organization_id: uuid.UUID
) -> set[uuid.UUID]:
    """Return every active member (any role) of an organization."""
    rows = (
        db.query(OrganizationMembership.user_id)
        .filter(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.active.is_(True),
        )
        .all()
    )
    return {row.user_id for row in rows}


def effective_owner_user_ids(db: Session, asset: PolymorphicOwnable) -> set[uuid.UUID]:
    """Return the users with owner-equivalent powers on a polymorphic asset.

    For a user-owned asset this is just the owner; for an org-owned asset
    it is the set of active organization owners (FR-107 / NFR-006).
    """
    if asset.owner_user_id is not None:
        return {asset.owner_user_id}
    if asset.owner_organization_id is not None:
        return active_org_owner_user_ids(db, asset.owner_organization_id)
    return set()


def effective_requester_user_ids(db: Session, request: Request) -> set[uuid.UUID]:
    """Return the users with requester-equivalent powers on a Request (FR-039).

    Mirrors :func:`effective_owner_user_ids` but reads the ``requester_*``
    FK pair: for a user-requested campaign this is just the requester; for
    an org-requested one it is the set of active organization owners.
    """
    if request.requester_user_id is not None:
        return {request.requester_user_id}
    if request.requester_organization_id is not None:
        return active_org_owner_user_ids(db, request.requester_organization_id)
    return set()


def effective_cc_member_user_ids(
    db: Session, collection_center_id: uuid.UUID, asset: PolymorphicOwnable
) -> set[uuid.UUID]:
    """Return the users with member-equivalent powers on a Collection Center.

    Per-center contributors, plus the user-owner (if user-owned) or all
    active members of the owning organization (if org-owned). See
    ``database-schema.md`` §"Effective Members".
    """
    member_ids: set[uuid.UUID] = set()

    rows = (
        db.query(CollectionCenterMembership.user_id)
        .filter(
            CollectionCenterMembership.collection_center_id == collection_center_id,
            CollectionCenterMembership.active.is_(True),
        )
        .all()
    )
    member_ids.update(row.user_id for row in rows)

    if asset.owner_user_id is not None:
        member_ids.add(asset.owner_user_id)
    elif asset.owner_organization_id is not None:
        member_ids.update(active_org_member_user_ids(db, asset.owner_organization_id))

    return member_ids


def assert_caller_can_own_on_behalf_of(
    db: Session, caller: User, owner_organization_id: uuid.UUID | None
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Resolve the owner FKs for a create payload (owner-field convention).

    If ``owner_organization_id`` is given, the caller must be an active
    member of that org (else ``ORG_MEMBERSHIP_REQUIRED``) and the asset is
    org-owned. Otherwise the caller owns the asset personally. Returns the
    ``(owner_user_id, owner_organization_id)`` pair to persist.
    """
    if owner_organization_id is None:
        return caller.id, None
    if caller.id not in active_org_member_user_ids(db, owner_organization_id):
        raise OrgMembershipRequiredExceptionError
    return None, owner_organization_id
