"""Resource catalog HTTP routes (Phase 4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser, MaintainerUser

from . import schemas, service
from .constants import ResourceCategory, ResourceStatus

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=list[schemas.ResourceResponse])
async def list_resources(
    db: Annotated[Session, Depends(get_db)],
    tag: Annotated[str | None, Query()] = None,
    status: Annotated[ResourceStatus | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    category: Annotated[ResourceCategory | None, Query()] = None,
) -> list[schemas.ResourceResponse]:
    """List the public Resource catalog (FR-021).

    Filterable by tag/status/search and, for the future generic-supply
    catalog, by ``category``.
    """
    resources = service.list_resources(db, tag, status, search, category)
    return [schemas.ResourceResponse.model_validate(p) for p in resources]


@router.get("/stats", response_model=list[schemas.ResourceStats])
async def list_resource_stats(
    db: Annotated[Session, Depends(get_db)],
) -> list[schemas.ResourceStats]:
    """Requests-vs-claims counts for every Resource that has any activity.

    Declared before ``/{resource_id}`` so the literal path wins over the
    UUID matcher. The parts catalog merges this into its cards by id.
    """
    stats = service.request_claim_stats(db)
    return [
        schemas.ResourceStats(resource_id=rid, **counts)
        for rid, counts in stats.items()
    ]


@router.post("", response_model=schemas.ResourceResponse, status_code=201)
async def create_resource(
    payload: schemas.ResourceCreate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceResponse:
    """Register a Resource; owner defaults to the caller (FR-015)."""
    resource = service.create_resource(db, payload, actor)
    return schemas.ResourceResponse.model_validate(resource)


@router.get("/{resource_id}", response_model=schemas.ResourceResponse)
async def get_resource(
    resource_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceResponse:
    """Get a single Resource (public)."""
    resource = service.get_or_raise(db, resource_id)
    return schemas.ResourceResponse.model_validate(resource)


@router.get("/{resource_id}/stats", response_model=schemas.ResourceStats)
async def get_resource_stats(
    resource_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceStats:
    """Requests-vs-claims counts for a single Resource (public)."""
    # 404 if the Resource does not exist, for a clean detail-page contract.
    service.get_or_raise(db, resource_id)
    counts = service.resource_stats(db, resource_id)
    return schemas.ResourceStats(resource_id=resource_id, **counts)


@router.put("/{resource_id}", response_model=schemas.ResourceResponse)
async def update_resource(
    resource_id: UUID,
    payload: schemas.ResourceUpdate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceResponse:
    """Edit a Resource (effective owner)."""
    resource = service.update_resource(db, resource_id, payload, actor)
    return schemas.ResourceResponse.model_validate(resource)


@router.post("/{resource_id}/discontinue", response_model=schemas.ResourceResponse)
async def discontinue_resource(
    resource_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceResponse:
    """Mark a Resource discontinued (effective owner, FR-075)."""
    resource = service.set_status(db, resource_id, ResourceStatus.DISCONTINUED, actor)
    return schemas.ResourceResponse.model_validate(resource)


@router.post("/{resource_id}/reactivate", response_model=schemas.ResourceResponse)
async def reactivate_resource(
    resource_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceResponse:
    """Reactivate a discontinued Resource (effective owner)."""
    resource = service.set_status(db, resource_id, ResourceStatus.ACTIVE, actor)
    return schemas.ResourceResponse.model_validate(resource)


@router.post("/{resource_id}/archive", response_model=schemas.ResourceResponse)
async def archive_resource(
    resource_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceResponse:
    """Owner-side archive; blocked if open Requests reference it (FR-076)."""
    resource = service.archive_resource(db, resource_id, actor)
    return schemas.ResourceResponse.model_validate(resource)


@router.post("/{resource_id}/force-archive", response_model=schemas.ResourceResponse)
async def force_archive_resource(
    resource_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ResourceResponse:
    """Maintainer/admin force-archive; cascades open items closed (FR-077)."""
    resource = service.force_archive_resource(db, resource_id, actor)
    return schemas.ResourceResponse.model_validate(resource)
