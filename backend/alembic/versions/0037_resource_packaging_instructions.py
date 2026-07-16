"""Add packaging instructions to resources.

A per-Resource free-text field where the catalog entry's creator/owner spells
out how finished copies should be packaged for drop-off (e.g. "group in sets
of 4; each must carry the printed label + QR"). Nullable free text so existing
resources are unaffected. Surfaced on every RequestItem that pulls the
Resource, replacing the campaign-level ``requests.packaging_instructions``
(which stays in the schema but is no longer edited from the UI).

Revision ID: 0037_resource_packaging
Revises: 0036_drop_review_note
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0037_resource_packaging"
down_revision: str | None = "0036_drop_review_note"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``packaging_instructions`` column to resources."""
    op.add_column(
        "resources",
        sa.Column("packaging_instructions", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``packaging_instructions`` column from resources."""
    op.drop_column("resources", "packaging_instructions")
