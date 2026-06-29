"""Pydantic request/response models for the uploads domain."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Public URL of a stored upload (image or file)."""

    url: str
