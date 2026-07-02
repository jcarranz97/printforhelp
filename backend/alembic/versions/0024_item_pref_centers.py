"""Per-item narrowing of a Request's preferred drop-off centers.

A Request can name several preferred collection centers, but a single item
may only be needed at some of them. This adds
``request_items.preferred_collection_center_ids`` (a subset of the Request's
list; empty means "all of them apply").

Revision ID: 0024_item_pref_centers
Revises: 0023_resource_units
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0024_item_pref_centers"
down_revision: str | None = "0023_resource_units"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "request_items",
        sa.Column(
            "preferred_collection_center_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("request_items", "preferred_collection_center_ids")
