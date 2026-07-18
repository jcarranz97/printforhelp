"""SQLAlchemy model for polymorphic reactions ("likes").

A ``Reaction`` is polymorphic over ``entity_type`` + ``entity_id`` (the same
pair used by watches, comments, and the activity log) so a single table covers
every reactable domain: collection centers, shipments, resources, requests,
request items, and comments. Un-reacting is a soft delete (``active = False``);
re-reacting reactivates the same row, so the partial unique index keeps at most
one active reaction per ``(user, entity, reaction_type)``.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import DEFAULT_REACTION_TYPE


class Reaction(BaseModel):
    """A single user's reaction to a polymorphic entity."""

    __tablename__ = "reactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # The kind of reaction. v1 is always ``"like"``; kept as a column so a
    # future multi-emoji feature needs no migration.
    reaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DEFAULT_REACTION_TYPE
    )

    __table_args__ = (
        Index(
            "uq_reactions_active",
            "user_id",
            "entity_type",
            "entity_id",
            "reaction_type",
            unique=True,
            postgresql_where=text("active"),
        ),
        Index("ix_reactions_entity", "entity_type", "entity_id"),
    )
