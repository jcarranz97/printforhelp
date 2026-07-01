"""HTTP routes for the item-tracking domain.

Two routers share this module:

- ``tracking_router`` (``/tracking``) — authenticated, owner-facing: generate
  tracking, read the owner view, set visibility/members, download QR bundles,
  and edit a record's tags.
- ``public_router`` (``/track``) — the public QR landing surface: read a
  token's timeline, fetch its QR image, and append a record. Reads and writes
  are gated by the token's visibility, not by a login.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentActiveUser, OptionalUser

from . import qr, schemas, service

tracking_router = APIRouter(prefix="/tracking", tags=["tracking"])
public_router = APIRouter(prefix="/track", tags=["tracking"])

DatabaseDep = Annotated[Session, Depends(get_db)]


# --------------------------------------------------------------------------- #
# Owner-facing routes (/tracking)
# --------------------------------------------------------------------------- #
@tracking_router.post(
    "/contributions/{contribution_id}",
    response_model=schemas.OwnerTrackingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_tracking(
    contribution_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.OwnerTrackingResponse:
    """Generate a tracking group + one QR item per unit (maker/admin)."""
    service.generate_tracking(db, contribution_id, actor)
    return service.get_owner_view(db, contribution_id, actor)


@tracking_router.get(
    "/contributions/{contribution_id}",
    response_model=schemas.OwnerTrackingResponse,
)
async def get_tracking(
    contribution_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.OwnerTrackingResponse:
    """Owner view: group, items, members, and the full timeline."""
    return service.get_owner_view(db, contribution_id, actor)


@tracking_router.patch(
    "/groups/{group_id}",
    response_model=schemas.OwnerTrackingResponse,
)
async def update_tracking(
    group_id: UUID,
    payload: schemas.TrackingUpdate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.OwnerTrackingResponse:
    """Set visibility and the named group-visibility members (maker/admin)."""
    group = service.update_group(db, group_id, actor, payload)
    return service.get_owner_view(db, group.contribution_id, actor)


def _bundle_labels(
    db: Session, group_id: UUID, actor: CurrentActiveUser
) -> list[tuple[str, str]]:
    group_token, items = service.get_group_tokens(db, group_id, actor)
    labels = [("Group", qr.track_url(settings.PUBLIC_APP_BASE_URL, group_token))]
    labels += [
        (f"#{sequence}", qr.track_url(settings.PUBLIC_APP_BASE_URL, token))
        for sequence, token in items
    ]
    return labels


@tracking_router.get("/groups/{group_id}/qr-bundle.png")
async def qr_bundle_png(
    group_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> Response:
    """Printable PNG sheet with the group QR and every item QR (maker/admin)."""
    png = qr.bundle_png_bytes(_bundle_labels(db, group_id, actor))
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="tracking-{group_id}.png"',
            # QR content is derived from PUBLIC_APP_BASE_URL, so never let a
            # cache serve a copy generated with a stale base URL.
            "Cache-Control": "no-store",
        },
    )


@tracking_router.get("/groups/{group_id}/qr-bundle.pdf")
async def qr_bundle_pdf(
    group_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> Response:
    """Printable PDF sheet with the group QR and every item QR (maker/admin)."""
    pdf = qr.bundle_pdf_bytes(_bundle_labels(db, group_id, actor))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="tracking-{group_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@tracking_router.patch(
    "/records/{record_id}",
    response_model=schemas.TrackingRecordResponse,
)
async def edit_record_tags(
    record_id: UUID,
    payload: schemas.RecordTagsUpdate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.TrackingRecordResponse:
    """Edit a record's tags (author, contribution owner, or maintainer/admin)."""
    record, kind, token, maker_id, sequence = service.edit_record_tags(
        db, record_id, actor, payload.tags
    )
    return service.build_record_response(
        db,
        record,
        kind=kind,
        token=token,
        viewer=actor,
        maker_id=maker_id,
        item_sequence=sequence,
    )


# --------------------------------------------------------------------------- #
# Public routes (/track)
# --------------------------------------------------------------------------- #
@public_router.get("/{token}", response_model=schemas.PublicTrackingResponse)
async def public_view(
    token: str,
    viewer: OptionalUser,
    db: DatabaseDep,
    include_item_updates: Annotated[bool, Query()] = True,
) -> schemas.PublicTrackingResponse:
    """Public tracking page: item summary and its visibility-gated timeline.

    For a group token, ``include_item_updates`` (default) folds every per-item
    update into the timeline; pass False to show only group-level updates.
    """
    return service.get_public_view(db, token, viewer, include_item_updates)


@public_router.get("/{token}/qr.png")
async def token_qr_png(token: str, db: DatabaseDep) -> Response:
    """QR image (PNG) encoding this token's public tracking URL."""
    service.assert_token_exists(db, token)
    png = qr.qr_png_bytes(qr.track_url(settings.PUBLIC_APP_BASE_URL, token))
    return Response(
        content=png,
        media_type="image/png",
        # QR content is derived from PUBLIC_APP_BASE_URL, so never let a cache
        # serve a copy generated with a stale base URL.
        headers={"Cache-Control": "no-store"},
    )


@public_router.post(
    "/{token}/records",
    response_model=schemas.TrackingRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_record(
    token: str,
    payload: schemas.RecordCreate,
    viewer: OptionalUser,
    db: DatabaseDep,
) -> schemas.TrackingRecordResponse:
    """Append a record after scanning a QR (anonymous or attributed)."""
    kind, maker_id, record, sequence = service.add_record(db, token, viewer, payload)
    return service.build_record_response(
        db,
        record,
        kind=kind,
        token=token,
        viewer=viewer,
        maker_id=maker_id,
        item_sequence=sequence,
    )
