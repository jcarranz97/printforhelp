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
from .constants import QrBundleScope

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
    scope: QrBundleScope,
    include_labels: bool,
    include_message: bool,
    message_text: str | None,
    seq_from: int | None = None,
    seq_to: int | None = None,
) -> tuple[list[tuple[str, str]], "Image.Image | None", str | None, int | None]:
    """Assemble the QR captions, optional label image, and optional message.

    ``scope`` selects which QRs to include: the single group QR, the per-unit
    item QRs, or both (see :class:`QrBundleScope`). ``include_labels`` folds
    the Resource's label image in (when it has one), printing a stack of label
    copies before the QR pages; ``include_message`` folds the maker note in
    (drawn above each QR), using ``message_text`` (the live textarea content)
    or the default community message when it is blank.

    ``seq_from``/``seq_to`` narrow the per-unit QRs to a reprint window, so a
    count corrected from 283 to 300 prints only the 17 missing labels instead
    of a second full set. They do not affect the group QR.
    """
    ctx = service.get_bundle_context(db, group_id, actor)
    # Every caption carries the group's unit count — the group QR says how many
    # units the package holds ("Group · 20 items") and each unit QR says which
    # one it is out of that total ("#3/20"). The total is always the group's
    # full unit count, never the number of QRs the chosen ``scope`` (or reprint
    # window) prints: unit 290 of a 300-unit package reads "#290/300" whether
    # it came off the first print run or a reprint of the last seventeen.
    total_units = len(ctx.items)
    group_label = (
        service.group_caption(total_units),
        qr.track_url(settings.PUBLIC_APP_BASE_URL, ctx.group_token),
    )
    # A group-only bundle has no per-unit QRs to narrow, so an out-of-range
    # window is not an error there — it simply has nothing to say.
    selected = (
        ctx.items
        if scope is QrBundleScope.GROUP
        else service.select_bundle_items(ctx.items, seq_from, seq_to)
    )
    item_labels = [
        (
            service.item_caption(sequence, total_units),
            qr.track_url(settings.PUBLIC_APP_BASE_URL, token),
        )
        for sequence, token in selected
    ]
    labels: list[tuple[str, str]]
    if scope is QrBundleScope.GROUP:
        labels = [group_label]
    elif scope is QrBundleScope.INDIVIDUAL:
        labels = item_labels
    else:
        labels = [group_label, *item_labels]
    label_image = (
        service.load_label_image(ctx.label_image_url) if include_labels else None
    )
    labels_per_page = ctx.labels_per_page if include_labels else None
    message = service.resolve_bundle_message(message_text) if include_message else None
    return labels, label_image, message, labels_per_page


@tracking_router.get("/groups/{group_id}/qr-bundle.png")
def qr_bundle_png(
    group_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
    scope: Annotated[QrBundleScope, Query()] = QrBundleScope.BOTH,
    labels: Annotated[bool, Query()] = False,
    message: Annotated[bool, Query()] = False,
    message_text: Annotated[str | None, Query()] = None,
    seq_from: Annotated[int | None, Query(ge=1)] = None,
    seq_to: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    """Printable PNG sheet of QRs for a tracking group (maker/admin).

    ``scope`` selects the group QR, the per-unit QRs, or both. ``labels``
    stacks a grid of part-label copies above the QR grid; ``message`` prints a
    maker note above each QR. ``message_text`` overrides the saved note for
    this render (the live, possibly unsaved textarea). ``seq_from``/``seq_to``
    reprint only a window of the per-unit QRs.

    Deliberately ``def``, not ``async def``: rendering is blocking Pillow work
    (seconds, for a large group) and the label fetch is a blocking HTTP call,
    so FastAPI must run this in the threadpool. On the event loop it would
    stall every other request for the duration of the render.
    """
    caps, label_image, note, labels_per_page = _bundle_render_inputs(
        db,
        group_id,
        actor,
        scope=scope,
        include_labels=labels,
        include_message=message,
        message_text=message_text,
        seq_from=seq_from,
        seq_to=seq_to,
    )
    png = qr.bundle_png_bytes(caps, label_image, note, labels_per_page)
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
def qr_bundle_pdf(
    group_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
    scope: Annotated[QrBundleScope, Query()] = QrBundleScope.BOTH,
    labels: Annotated[bool, Query()] = False,
    message: Annotated[bool, Query()] = False,
    message_text: Annotated[str | None, Query()] = None,
    seq_from: Annotated[int | None, Query(ge=1)] = None,
    seq_to: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    """Printable PDF sheet of QRs for a tracking group (maker/admin).

    ``scope`` selects the group QR, the per-unit QRs, or both. ``labels``
    prints a page-run of part-label copies before the QR pages; ``message``
    prints a maker note above each QR. ``message_text`` overrides the saved
    note for this render (the live, possibly unsaved textarea).
    ``seq_from``/``seq_to`` reprint only a window of the per-unit QRs.

    ``def``, not ``async def`` — see :func:`qr_bundle_png`.
    """
    caps, label_image, note, labels_per_page = _bundle_render_inputs(
        db,
        group_id,
        actor,
        scope=scope,
        include_labels=labels,
        include_message=message,
        message_text=message_text,
        seq_from=seq_from,
        seq_to=seq_to,
    )
    pdf = qr.bundle_pdf_bytes(caps, label_image, note, labels_per_page)
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
    "/{token}/confirm-received",
    response_model=schemas.PublicTrackingResponse,
)
async def confirm_received(
    token: str,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.PublicTrackingResponse:
    """Mark the scanned package received at its center (center member/admin).

    Lives on the public scan surface because that is where receipt is actually
    observed: the center scans the QR and sees units the maker never advanced
    past ``claimed``/``prepared``. Returns the refreshed tracking view.
    """
    service.confirm_received_by_token(db, token, actor)
    return service.get_public_view(db, token, actor)


@public_router.patch(
    "/{token}/quantity",
    response_model=schemas.PublicTrackingResponse,
)
async def adjust_quantity(
    token: str,
    payload: schemas.TrackingQuantityUpdate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.PublicTrackingResponse:
    """Correct the scanned Contribution's unit count (maintainer/admin).

    Lives on the scan surface for the same reason ``confirm-received`` does:
    the discrepancy is discovered with the package open, on the page the
    center already has in front of it. The maker said 283, the box holds 300.

    Growing keeps every already-printed label valid and only mints QRs for the
    new trailing units; shrinking retires the surplus ones permanently.
    Returns the refreshed tracking view.
    """
    visible = service.adjust_quantity_by_token(db, token, payload.quantity, actor)
    return service.get_public_view(db, visible, actor)


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
