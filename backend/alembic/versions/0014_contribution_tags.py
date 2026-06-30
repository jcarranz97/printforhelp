"""Add maker tags to contributions.

Lets a maker attach free-form personal labels to their own contribution
(and filter "My Contributions" by them), the same way the Resource
catalog and Collection Centers already support tags. The column is
NOT NULL with an empty-array default so existing contributions stay
valid.

Revision ID: 0014_contribution_tags
Revises: 0013_cc_tags
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014_contribution_tags"
down_revision: str | None = "0013_cc_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``tags`` array column to contributions."""
    op.add_column(
        "contributions",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    """Drop the ``tags`` column from contributions."""
    op.drop_column("contributions", "tags")
