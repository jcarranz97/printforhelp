"""Add tags to collection centers.

Lets the directory filter centers by tag (e.g. "ferulas", "drop-off")
the same way the Resource catalog already does. The column is
NOT NULL with an empty-array default so existing centers stay valid.

Revision ID: 0013_cc_tags
Revises: 0012_cc_state
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013_cc_tags"
down_revision: str | None = "0012_cc_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``tags`` array column to collection centers."""
    op.add_column(
        "collection_centers",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    """Drop the ``tags`` column from collection centers."""
    op.drop_column("collection_centers", "tags")
