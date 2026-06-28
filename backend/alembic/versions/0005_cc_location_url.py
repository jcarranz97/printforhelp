"""Add an optional location URL (map link) to collection centers.

Stores a shareable map link (typically a Google Maps URL) so the public
directory can render a "view on map" hyperlink for each drop-off point.

Revision ID: 0005_cc_location_url
Revises: 0004_shipments_activity
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_cc_location_url"
down_revision: str | None = "0004_shipments_activity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``location_url`` column."""
    op.add_column(
        "collection_centers",
        sa.Column("location_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``location_url`` column."""
    op.drop_column("collection_centers", "location_url")
