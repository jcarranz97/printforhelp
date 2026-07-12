"""Request + RequestItem HTTP routes (Phase 4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.contributions import schemas as contribution_schemas
from app.database import get_db
from app.dependencies import CurrentActiveUser, MaintainerUser, OptionalUser

from . import schemas, service
from .constants import RequestStatus

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=list[schemas.RequestListItem])
async def list_requests(
    db: Annotated[Session, Depends(get_db)],
    viewer: OptionalUser,
    status: Annotated[RequestStatus | None, Query()] = None,
) -> list[schemas.RequestListItem]:
    """List campaigns with a derived help state (public, FR-040).

    With no ``status`` filter this returns open and fulfilled campaigns so the
    directory can also surface completed ones. Unpublished campaigns are
    included only for the viewers entitled to see them (FR-134).
    """
    requests = service.list_requests(db, status, viewer)
    return [service.build_list_item(db, r) for r in requests]


@router.get("/review-queue", response_model=list[schemas.RequestListItem])
async def list_review_queue(
    _actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[schemas.RequestListItem]:
    """List campaigns awaiting review, oldest first (maintainer/admin).

    Declared before ``/{request_id}`` so the literal path wins the match.
    """
    return [service.build_list_item(db, r) for r in service.list_review_queue(db)]


@router.post("", response_model=schemas.RequestDetailResponse, status_code=201)
async def create_request(
    payload: schemas.RequestCreate,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Create a Request, optionally with items (FR-038)."""
    request = service.create_request(db, payload, actor)
    return service.build_detail(db, request)


@router.get("/beneficiaries", response_model=list[str])
async def list_beneficiary_suggestions(
    _actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[str]:
    """Distinct beneficiary values for the create-project typeahead.

    Requires a session (only used by the create/edit forms); ``_actor`` gates
    auth. Declared before ``/{request_id}`` so the literal path wins the match.
    """
    return service.list_beneficiary_suggestions(db)


@router.get("/{request_id}", response_model=schemas.RequestDetailResponse)
async def get_request(
    request_id: UUID,
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Get a Request with its items + per-item progress.

    Public for published campaigns; an unpublished one 404s for anyone but its
    requesters and maintainers/admins, so a leaked link is worthless (FR-134).
    """
    request = service.get_request_or_raise(db, request_id)
    service.assert_can_view_request(db, request, viewer)
    return service.build_detail(db, request)


@router.get(
    "/{request_id}/items/{item_number}",
    response_model=schemas.RequestItemDetailResponse,
)
async def get_request_item(
    request_id: UUID,
    item_number: int,
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestItemDetailResponse:
    """Get one item (by its per-Request number) with context (FR-134 gated)."""
    return service.get_item_detail(db, request_id, item_number, viewer)


@router.get(
    "/{request_id}/items/{item_number}/contributions",
    response_model=list[contribution_schemas.ItemCommitmentResponse],
)
async def list_item_commitments(
    request_id: UUID,
    item_number: int,
    viewer: OptionalUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[contribution_schemas.ItemCommitmentResponse]:
    """List the commitments on one item, by its number (FR-134 gated)."""
    return service.list_item_commitments(db, request_id, item_number, viewer)


@router.post("/{request_id}/submit", response_model=schemas.RequestDetailResponse)
async def submit_request(
    request_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Send a draft campaign to the review queue (effective requester)."""
    request = service.submit_for_review(db, request_id, actor)
    return service.build_detail(db, request)


@router.post("/{request_id}/approve", response_model=schemas.RequestDetailResponse)
async def approve_request(
    request_id: UUID,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Publish a campaign awaiting review (maintainer/admin)."""
    request = service.approve_request(db, request_id, actor)
    return service.build_detail(db, request)


@router.post(
    "/{request_id}/request-changes", response_model=schemas.RequestDetailResponse
)
async def request_changes(
    request_id: UUID,
    payload: schemas.RequestReviewNote,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Send a campaign back to its author for more info (maintainer/admin)."""
    request = service.request_changes(db, request_id, payload.note, actor)
    return service.build_detail(db, request)


@router.post("/{request_id}/unpublish", response_model=schemas.RequestDetailResponse)
async def unpublish_request(
    request_id: UUID,
    payload: schemas.RequestRejectNote,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Hide a published campaign and put it back under review (FR-135).

    Maintainers/admins (the takedown path) or the campaign's own requesters.
    Authorization is enforced in the service.
    """
    request = service.unpublish_request(db, request_id, payload.note, actor)
    return service.build_detail(db, request)


@router.post("/{request_id}/reject", response_model=schemas.RequestDetailResponse)
async def reject_request(
    request_id: UUID,
    payload: schemas.RequestRejectNote,
    actor: MaintainerUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Turn a campaign down; it is never published (maintainer/admin)."""
    request = service.reject_request(db, request_id, payload.note, actor)
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


@router.post("/{request_id}/reopen", response_model=schemas.RequestDetailResponse)
async def reopen_request(
    request_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestDetailResponse:
    """Reopen a closed Request (undo an accidental close)."""
    request = service.reopen_request(db, request_id, actor)
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


@router.post(
    "/{request_id}/items/{item_id}/reopen",
    response_model=schemas.RequestItemResponse,
)
async def reopen_item(
    request_id: UUID,
    item_id: UUID,
    actor: CurrentActiveUser,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.RequestItemResponse:
    """Reopen a closed item on an open Request (undo an accidental close)."""
    return service.reopen_item(db, request_id, item_id, actor)
