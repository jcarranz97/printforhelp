"""Add resource label image and per-tracking contributor message.

- ``resources.label_image_url`` — an optional print-on-the-package label
  image (e.g. a "Donación médica" banner) that makers can fold into the QR
  bundle above each tracking QR.
- ``tracking_groups.contributor_message`` — an optional maker note printed
  next to each QR in the label bundle (NULL means "use the default community
  message" when the maker opts to include one).

Revision ID: 0019_labels_and_message
Revises: 0018_item_tracking
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_labels_and_message"
down_revision: str | None = "0018_item_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the two nullable columns."""
    op.add_column(
        "resources",
        sa.Column("label_image_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "tracking_groups",
        sa.Column("contributor_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop the two columns."""
    op.drop_column("tracking_groups", "contributor_message")
    op.drop_column("resources", "label_image_url")
