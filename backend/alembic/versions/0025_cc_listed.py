"""Private, request-specific drop-off locations (CollectionCenter.listed).

Adds ``collection_centers.listed``: ``False`` marks a private drop-off
location that belongs to a request but must stay out of the public Collection
Centers directory (so nobody browsing sends unrelated donations there). It is
still fetchable by id/URL and usable as a drop-off for the requests that
reference it. Existing centers backfill to listed.

Revision ID: 0025_cc_listed
Revises: 0024_item_pref_centers
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_cc_listed"
down_revision: str | None = "0024_item_pref_centers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "collection_centers",
        sa.Column(
            "listed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_index("ix_collection_centers_listed", "collection_centers", ["listed"])


def downgrade() -> None:
    op.drop_index("ix_collection_centers_listed", table_name="collection_centers")
    op.drop_column("collection_centers", "listed")
