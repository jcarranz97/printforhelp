"""Organization HTTP routes (Phase 2)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser, MaintainerUser, OptionalUser

from . import schemas, service
from .exceptions import OrganizationNotFoundExceptionError

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[schemas.OrganizationResponse])
async def list_organizations(
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
    country: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    verified: Annotated[bool | None, Query()] = None,
) -> list[schemas.OrganizationResponse]:
    """List verified organizations (public, FR-105)."""
    orgs = service.list_organizations(db, viewer, country, q, verified)
    return [schemas.OrganizationResponse.model_validate(o) for o in orgs]


@router.post("", response_model=schemas.OrganizationResponse, status_code=201)
async def create_organization(
    payload: schemas.OrganizationCreate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Create an organization; caller becomes owner (FR-095)."""
    org = service.create_organization(db, payload, actor)
    return schemas.OrganizationResponse.model_validate(org)


@router.get("/{organization_id}", response_model=schemas.OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Get an organization. Unverified ones are visible to members only."""
    org = service.get_or_raise(db, organization_id)
    visible = org.verified and org.active
    if not visible and (
        viewer is None or not service.can_view_unverified(db, org, viewer)
    ):
        raise OrganizationNotFoundExceptionError(organization_id)
    return schemas.OrganizationResponse.model_validate(org)


@router.put("/{organization_id}", response_model=schemas.OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    payload: schemas.OrganizationUpdate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Edit an organization (owner / maintainer / admin)."""
    org = service.update_organization(db, organization_id, payload, actor)
    return schemas.OrganizationResponse.model_validate(org)


@router.post("/{organization_id}/verify", response_model=schemas.OrganizationResponse)
async def verify_organization(
    organization_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Verify an organization (maintainer/admin, FR-096)."""
    org = service.verify_organization(db, organization_id, actor)
    return schemas.OrganizationResponse.model_validate(org)


@router.post(
    "/{organization_id}/revoke-verification",
    response_model=schemas.OrganizationResponse,
)
async def revoke_verification(
    organization_id: UUID,
    payload: schemas.RevokeVerification,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Revoke an organization's verification (maintainer/admin)."""
    org = service.revoke_verification(db, organization_id, payload.reason, actor)
    return schemas.OrganizationResponse.model_validate(org)


@router.post("/{organization_id}/archive", response_model=schemas.OrganizationResponse)
async def archive_organization(
    organization_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Archive an organization (owner / maintainer / admin, FR-104)."""
    org = service.archive_organization(db, organization_id, actor)
    return schemas.OrganizationResponse.model_validate(org)


@router.get(
    "/{organization_id}/members",
    response_model=list[schemas.MembershipResponse],
)
async def list_members(
    organization_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[schemas.MembershipResponse]:
    """List members. Members + maintainer/admin only."""
    org = service.get_or_raise(db, organization_id)
    if not service.can_view_unverified(db, org, actor):
        raise OrganizationNotFoundExceptionError(organization_id)
    return service.list_members(db, organization_id)


@router.post(
    "/{organization_id}/members",
    response_model=schemas.MembershipResponse,
    status_code=201,
)
async def add_member(
    organization_id: UUID,
    payload: schemas.AddMember,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.MembershipResponse:
    """Add an existing user as a member (owner, FR-098)."""
    return service.add_member(db, organization_id, payload.username, actor)


@router.delete("/{organization_id}/members/{user_id}", status_code=204)
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove a member (owner removes others; member removes self, FR-100)."""
    service.remove_member(db, organization_id, user_id, actor)


@router.post(
    "/{organization_id}/transfer-ownership",
    response_model=schemas.OrganizationResponse,
)
async def transfer_ownership(
    organization_id: UUID,
    payload: schemas.TransferOwnership,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Transfer ownership to an existing member (owner, FR-101)."""
    org = service.transfer_ownership(db, organization_id, payload.target_user_id, actor)
    return schemas.OrganizationResponse.model_validate(org)


@router.post(
    "/{organization_id}/force-transfer-ownership",
    response_model=schemas.OrganizationResponse,
)
async def force_transfer_ownership(
    organization_id: UUID,
    payload: schemas.TransferOwnership,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.OrganizationResponse:
    """Maintainer/admin rescue: assign ownership to any user (FR-102)."""
    org = service.force_transfer_ownership(
        db, organization_id, payload.target_user_id, actor
    )
    return schemas.OrganizationResponse.model_validate(org)
