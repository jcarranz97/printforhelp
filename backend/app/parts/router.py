"""Part catalog HTTP routes (Phase 4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser, MaintainerUser

from . import schemas, service
from .constants import PartStatus

router = APIRouter(prefix="/parts", tags=["parts"])


@router.get("", response_model=list[schemas.PartResponse])
async def list_parts(
    db: Annotated[Session, Depends(get_db)],
    tag: Annotated[str | None, Query()] = None,
    status: Annotated[PartStatus | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> list[schemas.PartResponse]:
    """List the public Part catalog, filterable by tag/status/search (FR-021)."""
    parts = service.list_parts(db, tag, status, search)
    return [schemas.PartResponse.model_validate(p) for p in parts]


@router.post("", response_model=schemas.PartResponse, status_code=201)
async def create_part(
    payload: schemas.PartCreate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PartResponse:
    """Register a Part; owner defaults to the caller (FR-015)."""
    part = service.create_part(db, payload, actor)
    return schemas.PartResponse.model_validate(part)


@router.get("/{part_id}", response_model=schemas.PartResponse)
async def get_part(
    part_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PartResponse:
    """Get a single Part (public)."""
    part = service.get_or_raise(db, part_id)
    return schemas.PartResponse.model_validate(part)


@router.put("/{part_id}", response_model=schemas.PartResponse)
async def update_part(
    part_id: UUID,
    payload: schemas.PartUpdate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PartResponse:
    """Edit a Part (effective owner)."""
    part = service.update_part(db, part_id, payload, actor)
    return schemas.PartResponse.model_validate(part)


@router.post("/{part_id}/discontinue", response_model=schemas.PartResponse)
async def discontinue_part(
    part_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PartResponse:
    """Mark a Part discontinued (effective owner, FR-075)."""
    part = service.set_status(db, part_id, PartStatus.DISCONTINUED, actor)
    return schemas.PartResponse.model_validate(part)


@router.post("/{part_id}/reactivate", response_model=schemas.PartResponse)
async def reactivate_part(
    part_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PartResponse:
    """Reactivate a discontinued Part (effective owner)."""
    part = service.set_status(db, part_id, PartStatus.ACTIVE, actor)
    return schemas.PartResponse.model_validate(part)


@router.post("/{part_id}/archive", response_model=schemas.PartResponse)
async def archive_part(
    part_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PartResponse:
    """Owner-side archive; blocked if open Requests reference it (FR-076)."""
    part = service.archive_part(db, part_id, actor)
    return schemas.PartResponse.model_validate(part)


@router.post("/{part_id}/force-archive", response_model=schemas.PartResponse)
async def force_archive_part(
    part_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.PartResponse:
    """Maintainer/admin force-archive; cascades open items closed (FR-077)."""
    part = service.force_archive_part(db, part_id, actor)
    return schemas.PartResponse.model_validate(part)
