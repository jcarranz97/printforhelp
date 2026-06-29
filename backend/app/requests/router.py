"""Request + RequestItem HTTP routes (Phase 4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser

from . import schemas, service
from .constants import RequestStatus

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=list[schemas.RequestResponse])
async def list_requests(
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[RequestStatus | None, Query()] = None,
) -> list[schemas.RequestResponse]:
    """List campaigns, ``open`` by default (public, FR-040)."""
    requests = service.list_requests(db, status)
    return [schemas.RequestResponse.model_validate(r) for r in requests]


@router.post("", response_model=schemas.RequestDetailResponse, status_code=201)
async def create_request(
    payload: schemas.RequestCreate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Create a Request, optionally with items (FR-038)."""
    request = service.create_request(db, payload, actor)
    return service.build_detail(db, request)


@router.get("/{request_id}", response_model=schemas.RequestDetailResponse)
async def get_request(
    request_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Get a Request with its items + per-item progress (public)."""
    request = service.get_request_or_raise(db, request_id)
    return service.build_detail(db, request)


@router.put("/{request_id}", response_model=schemas.RequestDetailResponse)
async def update_request(
    request_id: UUID,
    payload: schemas.RequestUpdate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Edit campaign metadata while open (effective requester, FR-042)."""
    request = service.update_request(db, request_id, payload, actor)
    return service.build_detail(db, request)


@router.post("/{request_id}/close", response_model=schemas.RequestDetailResponse)
async def close_request(
    request_id: UUID,
    payload: schemas.CloseRequest,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Close a Request, cascading items + claimed Contributions (FR-049)."""
    request = service.close_request(db, request_id, payload.reason, actor)
    return service.build_detail(db, request)


@router.post(
    "/{request_id}/items",
    response_model=schemas.RequestItemResponse,
    status_code=201,
)
async def add_item(
    request_id: UUID,
    payload: schemas.RequestItemCreate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestItemResponse:
    """Add a new RequestItem to an open Request (FR-122)."""
    return service.add_item(db, request_id, payload, actor)


@router.delete("/{request_id}/items/{item_id}", status_code=204)
async def remove_item(
    request_id: UUID,
    item_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove an item from an open Request (FR-123)."""
    service.remove_item(db, request_id, item_id, actor)


@router.patch(
    "/{request_id}/items/{item_id}",
    response_model=schemas.RequestItemResponse,
)
async def update_item(
    request_id: UUID,
    item_id: UUID,
    payload: schemas.RequestItemUpdate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestItemResponse:
    """Edit an open item's target/description/deadline (FR-120)."""
    return service.update_item(db, request_id, item_id, payload, actor)


@router.post(
    "/{request_id}/items/{item_id}/close",
    response_model=schemas.RequestItemResponse,
)
async def close_item(
    request_id: UUID,
    item_id: UUID,
    payload: schemas.CloseRequest,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestItemResponse:
    """Close one item without closing the parent Request (FR-124)."""
    return service.close_item(db, request_id, item_id, payload.reason, actor)
