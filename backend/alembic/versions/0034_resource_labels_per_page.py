"""Add labels-per-page to resources.

The creator of a printable part designs its label image at a size meant to
print N copies per A4 page (2, 3, 4, ...). This nullable integer records that
intent so the QR-bundle renderer sizes each printed label copy accordingly.
NULL means "automatic" (the renderer's default grid), so existing resources
are unaffected.

Revision ID: 0034_resource_labels_pp
Revises: 0033_request_packaging
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034_resource_labels_pp"
down_revision: str | None = "0033_request_packaging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``labels_per_page`` column to resources."""
    op.add_column(
        "resources",
        sa.Column("labels_per_page", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``labels_per_page`` column from resources."""
    op.drop_column("resources", "labels_per_page")
