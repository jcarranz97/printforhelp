"""Pydantic request/response models for the uploads domain."""

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    """Public URL of a stored upload."""

    url: str
