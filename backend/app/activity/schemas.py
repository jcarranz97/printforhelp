"""Pydantic request/response models for activity and comments."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import MAX_COMMENT_BODY_LENGTH, ActivityAction, EntityType


class ActorSummary(BaseModel):
    """Lightweight author/actor info embedded in feed responses.

    Carries the same avatar fields as the public profile so a feed can render
    the author's picture without a second round trip per comment. The crop
    defaults match a picture with no crop chosen, which also keeps the
    "(unknown)" placeholder a one-liner.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    avatar_crop_x: float = 0
    avatar_crop_y: float = 0
    avatar_crop_w: float = 100
    avatar_crop_h: float = 100


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
    """Payload for posting a new Markdown comment (FR-131).

    Passing ``parent_comment_id`` posts the comment as a reply. It must
    reference a comment on the same entity; a reply-to-a-reply is re-rooted
    onto the top-level comment server-side (single-level threads).
    """

    entity_type: EntityType
    entity_id: UUID
    body: str = Field(min_length=1, max_length=MAX_COMMENT_BODY_LENGTH)
    parent_comment_id: UUID | None = None

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
    # Null for a top-level comment; the id of the top-level comment this is a
    # reply to. Clients group replies under their parent to render a thread.
    parent_comment_id: UUID | None = None
    body: str
    edited_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Valid @mentions in the body, as ``{token written: current username}``
    # (the key lowercased). A mapping rather than a list because a mention of
    # a handle that has since been renamed still resolves — the client shows
    # the owner's *current* name and links to it, so an old comment does not
    # keep pointing at a name nobody answers to. Tokens that resolve to
    # nobody are absent, and the client leaves those as plain text.
    mentions: dict[str, str] = {}
