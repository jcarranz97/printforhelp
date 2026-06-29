"""Collection Center HTTP routes (Phase 2)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser, MaintainerUser, OptionalUser
from app.users.service import get_or_create_anonymous_user

from . import schemas, service
from .constants import CollectionCenterStatus
from .exceptions import CollectionCenterNotFoundExceptionError

router = APIRouter(prefix="/collection-centers", tags=["collection-centers"])


@router.get("", response_model=list[schemas.CollectionCenterResponse])
async def list_collection_centers(
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
    country: Annotated[str | None, Query()] = None,
    city: Annotated[str | None, Query()] = None,
    verified: Annotated[bool | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
) -> list[schemas.CollectionCenterResponse]:
    """List operational centers, verified or not (public, FR-072).

    Maintainers/admins may pass ``active=false`` to list archived centers
    (the restore queue); the filter is ignored for everyone else.
    """
    centers = service.list_collection_centers(
        db, viewer, country, city, verified, active
    )
    return [schemas.CollectionCenterResponse.model_validate(c) for c in centers]


@router.post("", response_model=schemas.CollectionCenterResponse, status_code=201)
async def create_collection_center(
    payload: schemas.CollectionCenterCreate,
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Register a collection center (open — no login required).

    Logged-in users own the center themselves (or, optionally, an org they
    belong to). Guests submit anonymously: the center is owned by the
    system ``anonymous`` account. Either way it starts unverified and is
    moderated by maintainers.
    """
    if viewer is not None:
        cc = service.create_collection_center(db, payload, viewer)
    else:
        anonymous = get_or_create_anonymous_user(db)
        cc = service.create_collection_center(
            db, payload, anonymous, on_behalf_of_org_allowed=False
        )
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.get(
    "/{collection_center_id}",
    response_model=schemas.CollectionCenterResponse,
)
async def get_collection_center(
    collection_center_id: UUID,
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Get a center.

    Any active, operational center is publicly visible whether or not it
    is verified (the ``verified`` flag drives a "No verificado" badge).
    Operationally inactive / archived centers stay restricted to their
    effective members and to maintainers/admins.
    """
    cc = service.get_or_raise(db, collection_center_id)
    public = cc.active and cc.status == CollectionCenterStatus.ACTIVE
    if not public and (
        viewer is None or not service.is_effective_member(db, cc, viewer)
    ):
        raise CollectionCenterNotFoundExceptionError(collection_center_id)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.put(
    "/{collection_center_id}",
    response_model=schemas.CollectionCenterResponse,
)
async def update_collection_center(
    collection_center_id: UUID,
    payload: schemas.CollectionCenterUpdate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Edit a center (effective member or mod/admin, FR-031)."""
    cc = service.update_collection_center(db, collection_center_id, payload, actor)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.post(
    "/{collection_center_id}/verify",
    response_model=schemas.CollectionCenterResponse,
)
async def verify_collection_center(
    collection_center_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Verify a center (maintainer/admin, FR-027)."""
    cc = service.verify_collection_center(db, collection_center_id, actor)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.post(
    "/{collection_center_id}/revoke-verification",
    response_model=schemas.CollectionCenterResponse,
)
async def revoke_verification(
    collection_center_id: UUID,
    payload: schemas.RevokeVerification,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Revoke a center's verification (maintainer/admin)."""
    cc = service.revoke_verification(db, collection_center_id, payload.reason, actor)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.post(
    "/{collection_center_id}/toggle-status",
    response_model=schemas.CollectionCenterResponse,
)
async def toggle_status(
    collection_center_id: UUID,
    payload: schemas.ToggleStatus,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Set a center's operational status (effective member, FR-078)."""
    cc = service.toggle_status(db, collection_center_id, payload.status, actor)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.post(
    "/{collection_center_id}/archive",
    response_model=schemas.CollectionCenterResponse,
)
async def archive_collection_center(
    collection_center_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Owner-side archive (effective owner, FR-079)."""
    cc = service.archive_collection_center(db, collection_center_id, actor)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.post(
    "/{collection_center_id}/force-archive",
    response_model=schemas.CollectionCenterResponse,
)
async def force_archive_collection_center(
    collection_center_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Maintainer/admin force-archive (FR-080)."""
    cc = service.force_archive_collection_center(db, collection_center_id, actor)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.post(
    "/{collection_center_id}/restore",
    response_model=schemas.CollectionCenterResponse,
)
async def restore_collection_center(
    collection_center_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.CollectionCenterResponse:
    """Restore an archived center (maintainer/admin)."""
    cc = service.restore_collection_center(db, collection_center_id, actor)
    return schemas.CollectionCenterResponse.model_validate(cc)


@router.get(
    "/{collection_center_id}/contributors",
    response_model=list[schemas.ContributorResponse],
)
async def list_contributors(
    collection_center_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[schemas.ContributorResponse]:
    """List per-center contributors (effective members + mod/admin)."""
    cc = service.get_or_raise(db, collection_center_id)
    if not service.is_effective_member(db, cc, actor):
        raise CollectionCenterNotFoundExceptionError(collection_center_id)
    return service.list_contributors(db, collection_center_id)


@router.post(
    "/{collection_center_id}/contributors",
    response_model=schemas.ContributorResponse,
    status_code=201,
)
async def add_contributor(
    collection_center_id: UUID,
    payload: schemas.AddContributor,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ContributorResponse:
    """Add a per-center contributor (effective owner, FR-084)."""
    return service.add_contributor(db, collection_center_id, payload.username, actor)


@router.delete("/{collection_center_id}/contributors/{user_id}", status_code=204)
async def remove_contributor(
    collection_center_id: UUID,
    user_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove a contributor (effective owner removes; contributor self-removes)."""
    service.remove_contributor(db, collection_center_id, user_id, actor)
