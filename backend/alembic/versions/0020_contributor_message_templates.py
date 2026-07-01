"""Move the contributor message from the tracking to the user.

Replaces the per-tracking ``tracking_groups.contributor_message`` column with
a user-owned ``contributor_messages`` table of reusable notes ("saved
replies"), so the same message can be picked and reused across every tracking
a maker manages.

Revision ID: 0020_contributor_templates
Revises: 0019_labels_and_message
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0020_contributor_templates"
down_revision: str | None = "0019_labels_and_message"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    ]


def upgrade() -> None:
    """Create the user-owned templates table; drop the per-group column."""
    op.create_table(
        "contributor_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_contributor_messages_user_id", "contributor_messages", ["user_id"]
    )
    op.drop_column("tracking_groups", "contributor_message")


def downgrade() -> None:
    """Restore the per-group column; drop the templates table."""
    op.add_column(
        "tracking_groups",
        sa.Column("contributor_message", sa.Text(), nullable=True),
    )
    op.drop_index("ix_contributor_messages_user_id", table_name="contributor_messages")
    op.drop_table("contributor_messages")
