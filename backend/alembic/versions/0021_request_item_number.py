"""Add a stable per-Request sequential number to RequestItems.

Each ``request_items`` row gets an ``item_number`` that starts at 1 within its
Request and increments (1, 2, 3, ...). This makes duplicate Resources on one
Request distinguishable ("Demo Splint #1" vs "#2") and gives each item a
short, shareable URL (``/requests/{id}/items/{n}``). Numbers are unique per
Request; existing rows are backfilled by creation order.

Revision ID: 0021_request_item_number
Revises: 0020_contributor_templates
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_request_item_number"
down_revision: str | None = "0020_contributor_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) Add the column nullable so existing rows can be backfilled first.
    op.add_column(
        "request_items",
        sa.Column("item_number", sa.Integer(), nullable=True),
    )
    # 2) Backfill: number each Request's items by creation order, starting at 1.
    op.execute(
        """
        UPDATE request_items AS ri
        SET item_number = numbered.rn
        FROM (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY request_id ORDER BY created_at, id
                   ) AS rn
            FROM request_items
        ) AS numbered
        WHERE ri.id = numbered.id
        """
    )
    # 3) Lock it down: required + unique per Request.
    op.alter_column("request_items", "item_number", nullable=False)
    op.create_unique_constraint(
        "uq_request_item_number", "request_items", ["request_id", "item_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_request_item_number", "request_items", type_="unique")
    op.drop_column("request_items", "item_number")
