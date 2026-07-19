"""Track username changes.

Users may now rename their public handle. Every rename is recorded here so the
change can be shown on their profile timeline, and so the cooldown between
renames is enforced from history rather than a mutable column that could drift.

Revision ID: 0043_username_changes
Revises: 0042_user_avatar_crop
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0043_username_changes"
down_revision: str | None = "0042_user_avatar_crop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the append-only ``username_changes`` table."""
    op.create_table(
        "username_changes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("from_username", sa.String(length=64), nullable=False),
        sa.Column("to_username", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )


def downgrade() -> None:
    """Drop the ``username_changes`` table."""
    op.drop_table("username_changes")
