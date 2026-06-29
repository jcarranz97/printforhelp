"""Upload HTTP routes — direct file uploads that return a public URL."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.dependencies import get_current_active_user

from . import schemas, service

# Auth is required for every upload route (set once at the router level so
# the handler does not bind an unused ``actor`` parameter).
router = APIRouter(
    prefix="/uploads",
    tags=["uploads"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post("/images", response_model=schemas.UploadResponse, status_code=201)
async def upload_image(
    file: Annotated[UploadFile, File()],
) -> schemas.UploadResponse:
    """Upload an image and get back its public URL (auth required)."""
    data = await file.read()
    url = service.store_image(data)
    return schemas.UploadResponse(url=url)


@router.post("/files", response_model=schemas.UploadResponse, status_code=201)
async def upload_file(
    file: Annotated[UploadFile, File()],
) -> schemas.UploadResponse:
    """Upload a model/source file and get back its public URL (auth required).

    Lets makers host designs on PrintForHelp; the returned URL is used as a
    Resource's ``source_url`` so the "download" link points at us.
    """
    data = await file.read()
    url = service.store_file(data, file.filename)
    return schemas.UploadResponse(url=url)
