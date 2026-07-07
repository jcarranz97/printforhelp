"""Add packaging instructions to requests.

A campaign-level free-text field where a requester spells out how finished
items should be packaged for drop-off (e.g. "group the toys in sets of 4;
each toy must include the printed label and QR from the page"). Nullable
free text so existing requests are unaffected.

Revision ID: 0033_request_packaging
Revises: 0032_request_beneficiary
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0033_request_packaging"
down_revision: str | None = "0032_request_beneficiary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``packaging_instructions`` column to requests."""
    op.add_column(
        "requests",
        sa.Column("packaging_instructions", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop the ``packaging_instructions`` column from requests."""
    op.drop_column("requests", "packaging_instructions")
