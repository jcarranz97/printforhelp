"""Add an optional state/province to collection centers.

Lets the directory filter centers by state (e.g. only those in "CA") in
addition to country and city. The column is nullable so existing centers
created before this field keep working; the value is backfilled over time
and required only on new submissions from the frontend.

Revision ID: 0012_cc_state
Revises: 0011_contribution_prepared
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_cc_state"
down_revision: str | None = "0011_contribution_prepared"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``state`` column to collection centers."""
    op.add_column(
        "collection_centers",
        sa.Column("state", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``state`` column from collection centers."""
    op.drop_column("collection_centers", "state")
