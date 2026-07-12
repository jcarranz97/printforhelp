"""Contribution lifecycle HTTP routes (Phase 4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser

from . import schemas, service
from .constants import ContributionStatus

router = APIRouter(prefix="/contributions", tags=["contributions"])


@router.post("", response_model=schemas.ContributionResponse, status_code=201)
async def create_contribution(
    payload: schemas.ContributionCreate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ContributionResponse:
    """Claim a quantity of an open RequestItem (FR-050)."""
    contribution = service.create_contribution(db, payload, actor)
    return schemas.ContributionResponse.model_validate(contribution)


@router.get("/me", response_model=list[schemas.MyContributionResponse])
async def list_my_contributions(
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[ContributionStatus | None, Query()] = None,
) -> list[schemas.MyContributionResponse]:
    """List the caller's Contributions with Resource + Request context."""
    return service.list_my_contributions(db, actor, status)


@router.patch("/{contribution_id}", response_model=schemas.ContributionResponse)
async def update_contribution(
    contribution_id: UUID,
    payload: schemas.ContributionUpdate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ContributionResponse:
    """Edit quantity/notes/center before delivery (maker, FR-057)."""
    contribution = service.update_contribution(db, contribution_id, payload, actor)
    return schemas.ContributionResponse.model_validate(contribution)


@router.post(
    "/{contribution_id}/mark-prepared",
    response_model=schemas.ContributionResponse,
)
async def mark_prepared(
    contribution_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ContributionResponse:
    """Advance ``claimed -> prepared`` (maker, FR-053)."""
    contribution = service.mark_prepared(db, contribution_id, actor)
    return schemas.ContributionResponse.model_validate(contribution)


@router.post(
    "/{contribution_id}/mark-delivered",
    response_model=schemas.ContributionResponse,
)
async def mark_delivered(
    contribution_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ContributionResponse:
    """Advance ``prepared -> delivered``; auto-receive per FR-126."""
    contribution = service.mark_delivered(db, contribution_id, actor)
    return schemas.ContributionResponse.model_validate(contribution)


@router.post(
    "/{contribution_id}/confirm-received",
    response_model=schemas.ContributionResponse,
)
async def confirm_received(
    contribution_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ContributionResponse:
    """Confirm ``delivered -> received`` (effective CC member, FR-056)."""
    contribution = service.confirm_received(db, contribution_id, actor)
    return schemas.ContributionResponse.model_validate(contribution)


@router.post(
    "/{contribution_id}/release",
    response_model=schemas.ContributionResponse,
)
async def release_contribution(
    contribution_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.ContributionResponse:
    """Release a claimed/prepared Contribution (maker, FR-054)."""
    contribution = service.release(db, contribution_id, actor)
    return schemas.ContributionResponse.model_validate(contribution)
