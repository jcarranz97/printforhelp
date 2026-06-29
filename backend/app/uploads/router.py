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


@router.post("/images", response_model=schemas.ImageUploadResponse, status_code=201)
async def upload_image(
    file: Annotated[UploadFile, File()],
) -> schemas.ImageUploadResponse:
    """Upload an image and get back its public URL (auth required)."""
    data = await file.read()
    url = service.store_image(data)
    return schemas.ImageUploadResponse(url=url)
