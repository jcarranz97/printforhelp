"""Site notices HTTP routes (page banners + per-entity notices)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser, MaintainerUser

from . import schemas, service
from .constants import NoticeStatus, NoticeTargetType, PageScope

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("", response_model=list[schemas.NoticeResponse])
async def list_notices(
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[PageScope | None, Query()] = None,
    target_type: Annotated[NoticeTargetType | None, Query()] = None,
    target_id: Annotated[UUID | None, Query()] = None,
) -> list[schemas.NoticeResponse]:
    """List public notices: page banners by ``scope`` or an entity's notices."""
    notices = service.list_public(db, scope, target_type, target_id)
    return service.serialize_many(db, notices)


@router.get("/manage", response_model=list[schemas.NoticeResponse])
async def list_manage(
    _actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[NoticeStatus | None, Query()] = None,
) -> list[schemas.NoticeResponse]:
    """List every active notice for moderation (maintainer/admin)."""
    notices = service.list_manage(db, status)
    return service.serialize_many(db, notices)


@router.post("", response_model=schemas.NoticeResponse, status_code=201)
async def create_notice(
    payload: schemas.NoticeCreate,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.NoticeResponse:
    """Create an approved notice directly (maintainer/admin)."""
    notice = service.create_notice(db, payload, actor)
    return service.serialize_one(db, notice)


@router.post("/request", response_model=schemas.NoticeResponse, status_code=201)
async def request_notice(
    payload: schemas.NoticeRequest,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.NoticeResponse:
    """Request an entity notice (owner -> pending, maintainer -> approved)."""
    notice = service.request_notice(db, payload, actor)
    return service.serialize_one(db, notice)


@router.post("/{notice_id}/approve", response_model=schemas.NoticeResponse)
async def approve_notice(
    notice_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.NoticeResponse:
    """Approve a pending notice (maintainer/admin)."""
    notice = service.approve(db, notice_id, actor)
    return service.serialize_one(db, notice)


@router.post("/{notice_id}/decline", response_model=schemas.NoticeResponse)
async def decline_notice(
    notice_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
    payload: schemas.NoticeDecline | None = None,
) -> schemas.NoticeResponse:
    """Decline a pending notice (maintainer/admin); reason is optional."""
    reason = payload.reason if payload is not None else None
    notice = service.decline(db, notice_id, reason, actor)
    return service.serialize_one(db, notice)


@router.post("/{notice_id}/toggle", response_model=schemas.NoticeResponse)
async def toggle_notice(
    notice_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.NoticeResponse:
    """Enable or disable a notice (maintainer/admin)."""
    notice = service.toggle_enabled(db, notice_id, actor)
    return service.serialize_one(db, notice)


@router.patch("/{notice_id}", response_model=schemas.NoticeResponse)
async def update_notice(
    notice_id: UUID,
    payload: schemas.NoticeUpdate,
    _actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.NoticeResponse:
    """Edit a notice's severity, scopes and/or translations (maintainer)."""
    notice = service.update_notice(db, notice_id, payload)
    return service.serialize_one(db, notice)


@router.delete("/{notice_id}", response_model=schemas.NoticeResponse)
async def delete_notice(
    notice_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.NoticeResponse:
    """Archive a notice (maintainer, or the requester of a pending one)."""
    notice = service.soft_delete(db, notice_id, actor)
    return service.serialize_one(db, notice)
