"""HTTP routes for polymorphic reactions ("likes").

All routes are ``/reactions``. Reads are public (a logged-out visitor still
sees counts; ``reacted`` is always false for them); reacting / un-reacting
requires an authenticated active user and only ever affects that user's own
reaction.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.database import get_db
from app.dependencies import CurrentActiveUser, OptionalUser

from . import schemas, service
from .constants import MAX_BATCH_ENTITY_IDS

router = APIRouter(prefix="/reactions", tags=["reactions"])

DatabaseDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[schemas.ReactionState])
async def list_reaction_states(
    db: DatabaseDep,
    viewer: OptionalUser,
    entity_type: Annotated[EntityType, Query()],
    entity_id: Annotated[
        list[uuid.UUID], Query(min_length=1, max_length=MAX_BATCH_ENTITY_IDS)
    ],
) -> list[schemas.ReactionState]:
    """Reaction ``(count, reacted)`` for one or many entities of a type.

    A single ``entity_id`` powers a detail page's heart; the repeated form
    powers a comment feed, fetching every visible comment's state at once.
    """
    states = service.get_states(
        db, entity_type=entity_type, entity_ids=entity_id, viewer=viewer
    )
    return [
        schemas.ReactionState(
            entity_type=entity_type,
            entity_id=eid,
            count=count,
            reacted=reacted,
        )
        for eid, (count, reacted) in states.items()
    ]


@router.post("", response_model=schemas.ReactionState)
async def create_reaction(
    payload: schemas.ReactionCreate,
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ReactionState:
    """React to an entity (idempotent). Returns the updated state."""
    count, reacted = service.react(
        db, user=user, entity_type=payload.entity_type, entity_id=payload.entity_id
    )
    return schemas.ReactionState(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        count=count,
        reacted=reacted,
    )


@router.delete("/{entity_type}/{entity_id}", response_model=schemas.ReactionState)
async def delete_reaction(
    entity_type: EntityType,
    entity_id: uuid.UUID,
    user: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ReactionState:
    """Remove the current user's reaction from an entity. Returns the state."""
    count, reacted = service.unreact(
        db, user=user, entity_type=entity_type, entity_id=entity_id
    )
    return schemas.ReactionState(
        entity_type=entity_type,
        entity_id=entity_id,
        count=count,
        reacted=reacted,
    )
