"""Add the reactions ("likes") table.

A polymorphic ``reactions`` table over ``entity_type`` + ``entity_id`` (the
same pair used by watches and comments). Un-reacting is a soft delete; the
partial unique index keeps at most one active reaction per
``(user, entity, reaction_type)``.

Revision ID: 0039_reactions
Revises: 0038_notification_email_prefs
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0039_reactions"
down_revision: str | None = "0038_notification_email_prefs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the reactions table and its indexes."""
    op.create_table(
        "reactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reaction_type", sa.String(length=20), nullable=False),
    )
    op.create_index("ix_reactions_user_id", "reactions", ["user_id"])
    op.create_index(
        "ix_reactions_entity",
        "reactions",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "uq_reactions_active",
        "reactions",
        ["user_id", "entity_type", "entity_id", "reaction_type"],
        unique=True,
        postgresql_where=sa.text("active"),
    )


def downgrade() -> None:
    """Drop the reactions table."""
    op.drop_index("uq_reactions_active", table_name="reactions")
    op.drop_index("ix_reactions_entity", table_name="reactions")
    op.drop_index("ix_reactions_user_id", table_name="reactions")
    op.drop_table("reactions")
