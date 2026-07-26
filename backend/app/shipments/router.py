"""Shipment HTTP routes, nested under a Collection Center (FR-127..130)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentActiveUser, OptionalUser
from app.tracking import qr
from app.users.models import User

from . import schemas, service

router = APIRouter(
    prefix="/collection-centers/{collection_center_id}/shipments",
    tags=["shipments"],
)

DatabaseDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[schemas.ShipmentResponse])
async def list_shipments(
    collection_center_id: UUID,
    db: DatabaseDep,
) -> list[schemas.ShipmentResponse]:
    """List a center's shipments (public — always visible, FR-130)."""
    shipments = service.list_shipments(db, collection_center_id)
    return [schemas.ShipmentResponse.model_validate(s) for s in shipments]


@router.get("/{shipment_id}", response_model=schemas.ShipmentResponse)
async def get_shipment(
    collection_center_id: UUID,
    shipment_id: UUID,
    db: DatabaseDep,
) -> schemas.ShipmentResponse:
    """Get a single shipment (public — always visible, FR-130)."""
    shipment = service.get_or_raise(db, collection_center_id, shipment_id)
    return schemas.ShipmentResponse.model_validate(shipment)


@router.post(
    "", response_model=schemas.ShipmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_shipment(
    collection_center_id: UUID,
    payload: schemas.ShipmentCreate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentResponse:
    """Create a shipment (effective member or maintainer/admin, FR-129)."""
    shipment = service.create_shipment(db, collection_center_id, payload, actor)
    return schemas.ShipmentResponse.model_validate(shipment)


@router.patch("/{shipment_id}", response_model=schemas.ShipmentResponse)
async def update_shipment(
    collection_center_id: UUID,
    shipment_id: UUID,
    payload: schemas.ShipmentUpdate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentResponse:
    """Edit a shipment, including its status (FR-129)."""
    shipment = service.update_shipment(
        db, collection_center_id, shipment_id, payload, actor
    )
    return schemas.ShipmentResponse.model_validate(shipment)


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipment(
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> None:
    """Soft-delete a shipment (effective member or maintainer/admin)."""
    service.delete_shipment(db, collection_center_id, shipment_id, actor)


def _label_response(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: User,
    *,
    as_pdf: bool,
    manifest: bool,
) -> Response:
    """Render the box label, shared by the PNG and PDF routes."""
    shipment, ctx = service.box_label_context(
        db, collection_center_id, shipment_id, actor
    )
    url = qr.track_url(settings.PUBLIC_APP_BASE_URL, shipment.tracking_token)
    if as_pdf:
        content = qr.box_label_pdf_bytes(
            url,
            title=ctx.title,
            subtitle=ctx.subtitle,
            lines=ctx.lines,
            manifest_header=ctx.manifest_header if manifest else None,
            manifest_rows=ctx.manifest_rows,
        )
        media_type, suffix = "application/pdf", "pdf"
    else:
        content = qr.box_label_png_bytes(
            url, title=ctx.title, subtitle=ctx.subtitle, lines=ctx.lines
        )
        media_type, suffix = "image/png", "png"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (f'inline; filename="caja-{shipment_id}.{suffix}"'),
            # The QR encodes PUBLIC_APP_BASE_URL, so never let a cache serve a
            # sheet generated against a stale base URL.
            "Cache-Control": "no-store",
        },
    )


@router.get("/{shipment_id}/label.png")
def shipment_label_png(
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> Response:
    """Printable box label as a PNG (FR-149).

    Deliberately ``def``, not ``async def``: the render is blocking Pillow
    work, so FastAPI must run it in the threadpool rather than stalling the
    event loop.
    """
    return _label_response(
        db, collection_center_id, shipment_id, actor, as_pdf=False, manifest=False
    )


@router.get("/{shipment_id}/label.pdf")
def shipment_label_pdf(
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
    manifest: Annotated[bool, Query()] = True,
) -> Response:
    """Printable box label as A4 PDF, followed by the manifest (FR-149).

    The manifest is the checklist the receiving team ticks off against what
    actually comes out of the box, so it is on by default.
    """
    return _label_response(
        db, collection_center_id, shipment_id, actor, as_pdf=True, manifest=manifest
    )


@router.post("/{shipment_id}/dispatch", response_model=schemas.ShipmentResponse)
async def dispatch_shipment(
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentResponse:
    """Send the box on its way, freezing its manifest (FR-141)."""
    shipment = service.dispatch(db, collection_center_id, shipment_id, actor)
    return schemas.ShipmentResponse.model_validate(shipment)


@router.post("/{shipment_id}/arrive", response_model=schemas.ShipmentArrivalResponse)
async def arrive_shipment(
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentArrivalResponse:
    """Sign for the box and confirm every Contribution inside it (FR-143).

    Open to the staff of the box's **destination** center as well as its
    origin: at a relay hop the people holding the box work for neither the
    maker's drop-off center nor, necessarily, the final one (FR-144).
    """
    shipment, result = service.mark_arrived(
        db, collection_center_id, shipment_id, actor
    )
    return schemas.ShipmentArrivalResponse(
        shipment=schemas.ShipmentResponse.model_validate(shipment),
        received=result.received,
        skipped_already=result.skipped_already,
        skipped_no_center=result.skipped_no_center,
        packages_total=result.packages_total,
    )


@router.post(
    "/{shipment_id}/receive-contents",
    response_model=schemas.ShipmentArrivalResponse,
)
async def receive_shipment_contents(
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentArrivalResponse:
    """Re-run the bulk receipt without changing status (idempotent, FR-143)."""
    result = service.receive_contents(db, collection_center_id, shipment_id, actor)
    shipment = service.get_or_raise(db, collection_center_id, shipment_id)
    return schemas.ShipmentArrivalResponse(
        shipment=schemas.ShipmentResponse.model_validate(shipment),
        received=result.received,
        skipped_already=result.skipped_already,
        skipped_no_center=result.skipped_no_center,
        packages_total=result.packages_total,
    )


@router.get("/{shipment_id}/contents", response_model=schemas.ShipmentContentsResponse)
async def list_contents(
    collection_center_id: UUID,
    shipment_id: UUID,
    viewer: OptionalUser,
    db: DatabaseDep,
) -> schemas.ShipmentContentsResponse:
    """Read a box's manifest (public, redacted per viewer — FR-146).

    Anyone may see what a box weighs in aggregate; only the staff of its origin
    or destination center — and the owners of the packages themselves — see the
    lines describing what is inside.
    """
    return service.list_contents(db, collection_center_id, shipment_id, viewer)


@router.post(
    "/{shipment_id}/contents",
    response_model=schemas.ShipmentContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_content(
    collection_center_id: UUID,
    shipment_id: UUID,
    payload: schemas.ShipmentContentCreate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentContentResponse:
    """Pack a package or another box into this shipment (FR-138)."""
    content = service.add_content(db, collection_center_id, shipment_id, payload, actor)
    return schemas.ShipmentContentResponse.model_validate(content)


@router.delete(
    "/{shipment_id}/contents/{content_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_content(
    collection_center_id: UUID,
    shipment_id: UUID,
    content_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> None:
    """Unpack one manifest line (soft delete, FR-147)."""
    service.remove_content(db, collection_center_id, shipment_id, content_id, actor)
