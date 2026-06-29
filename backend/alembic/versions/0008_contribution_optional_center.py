"""Make contributions.collection_center_id optional.

Makers can commit to print before they have a drop-off Collection Center
and assign one later (before marking the Contribution delivered).

Revision ID: 0008_contrib_center
Revises: 0007_cc_description
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_contrib_center"
down_revision: str | None = "0007_cc_description"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the NOT NULL on contributions.collection_center_id."""
    op.alter_column(
        "contributions",
        "collection_center_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    """Restore NOT NULL (rows without a center must be backfilled first)."""
    op.alter_column(
        "contributions",
        "collection_center_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
