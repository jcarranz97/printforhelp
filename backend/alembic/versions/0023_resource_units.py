"""Multiple suggested units per Resource + a chosen unit per RequestItem.

Supplies can carry several suggested units of measure (e.g. water in
"litros", "cajas", or "cubetas"), so the single ``resources.unit`` string
becomes a ``resources.units`` array. Each RequestItem then records the one
unit chosen for its quantity (seeded from the Resource's suggestions but
freely editable by the requester) via a new ``request_items.unit`` column.

Revision ID: 0023_resource_units_and_item_unit
Revises: 0022_user_flags
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0023_resource_units"
down_revision: str | None = "0022_user_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Resource: single unit -> list of suggested units.
    op.add_column(
        "resources",
        sa.Column(
            "units",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    # Backfill: fold any existing single unit into the new array.
    op.execute(
        "UPDATE resources SET units = ARRAY[unit] WHERE unit IS NOT NULL AND unit <> ''"
    )
    op.drop_column("resources", "unit")

    # RequestItem: the unit chosen for this item's quantity.
    op.add_column(
        "request_items",
        sa.Column("unit", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("request_items", "unit")

    op.add_column(
        "resources",
        sa.Column("unit", sa.String(length=32), nullable=True),
    )
    # Restore the first suggested unit into the single-value column.
    op.execute("UPDATE resources SET unit = units[1] WHERE array_length(units, 1) >= 1")
    op.drop_column("resources", "units")
