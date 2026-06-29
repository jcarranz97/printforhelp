"""Add an optional image URL to requests.

Lets a campaign carry a cover image (uploaded via /uploads/images or an
external URL) so request listings and detail pages look richer.

Revision ID: 0009_request_image
Revises: 0008_contrib_center
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_request_image"
down_revision: str | None = "0008_contrib_center"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``image_url`` column to requests."""
    op.add_column(
        "requests",
        sa.Column("image_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``image_url`` column from requests."""
    op.drop_column("requests", "image_url")
