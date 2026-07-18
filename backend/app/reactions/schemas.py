"""Pydantic request/response models for the reactions domain."""

from uuid import UUID

from pydantic import BaseModel

from app.activity.constants import EntityType


class ReactionCreate(BaseModel):
    """Payload for reacting to an entity.

    ``reaction_type`` is intentionally omitted in v1 (always the heart
    "like"); the service defaults it. It lives here so a future multi-emoji
    UI can start sending it without an API break.
    """

    entity_type: EntityType
    entity_id: UUID


class ReactionState(BaseModel):
    """The aggregate reaction state of one entity for the current viewer.

    Only the count and whether the viewer reacted are exposed; the identities
    of who reacted stay server-side for a possible future feature. ``by_author``
    is the "liked by the author" flag (Instagram-style) for comments — whether
    an owner of the comment's parent reacted to it; always ``False`` otherwise.
    """

    entity_type: EntityType
    entity_id: UUID
    count: int
    reacted: bool
    by_author: bool = False
