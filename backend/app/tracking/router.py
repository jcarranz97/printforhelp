"""HTTP routes for the item-tracking domain.

Two routers share this module:

- ``tracking_router`` (``/tracking``) — authenticated, owner-facing: generate
  tracking, read the owner view, set visibility/members, download QR bundles,
  and edit a record's tags.
- ``public_router`` (``/track``) — the public QR landing surface: read a
  token's timeline, fetch its QR image, and append a record. Reads and writes
  are gated by the token's visibility, not by a login.
"""

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentActiveUser, OptionalUser

from . import qr, schemas, service

if TYPE_CHECKING:
    from PIL import Image

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


@tracking_router.get(
    "/messages", response_model=list[schemas.ContributorMessageResponse]
)
async def list_contributor_messages(
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> list[schemas.ContributorMessageResponse]:
    """The current user's saved contributor-message templates, newest first."""
    rows = service.list_contributor_messages(db, actor)
    return [schemas.ContributorMessageResponse.model_validate(r) for r in rows]


@tracking_router.post(
    "/messages",
    response_model=schemas.ContributorMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contributor_message(
    payload: schemas.ContributorMessageCreate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ContributorMessageResponse:
    """Save a reusable message for the current user (dedupes identical text)."""
    row = service.create_contributor_message(db, actor, payload.body)
    return schemas.ContributorMessageResponse.model_validate(row)


@tracking_router.delete(
    "/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_contributor_message(
    message_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> None:
    """Delete one of the current user's saved messages."""
    service.delete_contributor_message(db, actor, message_id)


def _bundle_render_inputs(
    db: Session,
    group_id: UUID,
    actor: CurrentActiveUser,
    *,
    include_labels: bool,
    include_message: bool,
    message_text: str | None,
) -> tuple[list[tuple[str, str]], "Image.Image | None", str | None]:
    """Assemble the QR captions, optional label image, and optional message.

    ``include_labels`` folds the Resource's label image in (when it has one);
    ``include_message`` folds the maker note in, using ``message_text`` (the
    live textarea content) or the default community message when it is blank.
    Either inclusion switches the render to the sticker layout.
    """
    ctx = service.get_bundle_context(db, group_id, actor)
    labels = [("Group", qr.track_url(settings.PUBLIC_APP_BASE_URL, ctx.group_token))]
    labels += [
        (f"#{sequence}", qr.track_url(settings.PUBLIC_APP_BASE_URL, token))
        for sequence, token in ctx.items
    ]
    label_image = (
        service.load_label_image(ctx.label_image_url) if include_labels else None
    )
    message = service.resolve_bundle_message(message_text) if include_message else None
    return labels, label_image, message


@tracking_router.get("/groups/{group_id}/qr-bundle.png")
async def qr_bundle_png(
    group_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
    labels: Annotated[bool, Query()] = False,
    message: Annotated[bool, Query()] = False,
    message_text: Annotated[str | None, Query()] = None,
) -> Response:
    """Printable PNG sheet with the group QR and every item QR (maker/admin).

    ``labels`` / ``message`` opt each printed unit into the sticker layout
    (part label on top, maker note beside the QR). ``message_text`` overrides
    the saved note for this render (the live, possibly unsaved textarea).
    """
    caps, label_image, note = _bundle_render_inputs(
        db,
        group_id,
        actor,
        include_labels=labels,
        include_message=message,
        message_text=message_text,
    )
    png = qr.bundle_png_bytes(caps, label_image, note)
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
    labels: Annotated[bool, Query()] = False,
    message: Annotated[bool, Query()] = False,
    message_text: Annotated[str | None, Query()] = None,
) -> Response:
    """Printable PDF sheet with the group QR and every item QR (maker/admin).

    ``labels`` / ``message`` opt each printed unit into the sticker layout
    (part label on top, maker note beside the QR). ``message_text`` overrides
    the saved note for this render (the live, possibly unsaved textarea).
    """
    caps, label_image, note = _bundle_render_inputs(
        db,
        group_id,
        actor,
        include_labels=labels,
        include_message=message,
        message_text=message_text,
    )
    pdf = qr.bundle_pdf_bytes(caps, label_image, note)
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
