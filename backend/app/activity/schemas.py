"""Pydantic request/response models for activity and comments."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import MAX_COMMENT_BODY_LENGTH, ActivityAction, EntityType


class ActorSummary(BaseModel):
    """Lightweight author/actor info embedded in feed responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str


class ActivityResponse(BaseModel):
    """One row in a public activity timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: EntityType
    entity_id: UUID
    actor: ActorSummary
    action: ActivityAction
    changes: dict[str, Any]
    created_at: datetime


class CommentCreate(BaseModel):
    """Payload for posting a new Markdown comment (FR-131)."""

    entity_type: EntityType
    entity_id: UUID
    body: str = Field(min_length=1, max_length=MAX_COMMENT_BODY_LENGTH)

    @field_validator("body")
    @classmethod
    def _strip_and_require_nonempty(cls, value: str) -> str:
        """Strip surrounding whitespace; reject all-whitespace bodies."""
        stripped = value.strip()
        if not stripped:
            msg = "Comment body cannot be empty"
            raise ValueError(msg)
        return stripped


class CommentUpdate(BaseModel):
    """Payload for editing a comment body (author only, FR-132)."""

    body: str = Field(min_length=1, max_length=MAX_COMMENT_BODY_LENGTH)

    @field_validator("body")
    @classmethod
    def _strip_and_require_nonempty(cls, value: str) -> str:
        """Strip surrounding whitespace; reject all-whitespace bodies."""
        stripped = value.strip()
        if not stripped:
            msg = "Comment body cannot be empty"
            raise ValueError(msg)
        return stripped


class CommentResponse(BaseModel):
    """A single comment as returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: EntityType
    entity_id: UUID
    author: ActorSummary
    body: str
    edited_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Usernames mentioned in the body that resolve to a real active user,
    # so the client can highlight only valid @mentions.
    mentions: list[str] = []
