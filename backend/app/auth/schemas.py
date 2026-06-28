"""Pydantic request/response models for the auth domain."""

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """JWT issued on successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChange(BaseModel):
    """Change the authenticated user's own password (FR-005)."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    """Simple message envelope for action endpoints."""

    message: str
