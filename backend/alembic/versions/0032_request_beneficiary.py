"""Add a beneficiary field to requests.

Splits the single free-text project description into two focused prompts on
the create form: ``description`` keeps answering "what does the project seek
to solve?", while the new ``beneficiary`` column answers "who is the project
for?". Nullable free text so existing requests are unaffected.

Revision ID: 0032_request_beneficiary
Revises: 0031_org_handle
Create Date: 2026-07-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032_request_beneficiary"
down_revision: str | None = "0031_org_handle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``beneficiary`` column to requests."""
    op.add_column("requests", sa.Column("beneficiary", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop the ``beneficiary`` column from requests."""
    op.drop_column("requests", "beneficiary")
