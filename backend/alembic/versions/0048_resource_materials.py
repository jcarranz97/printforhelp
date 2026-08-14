"""Add the optional ``materials`` list to Resource.

Which filaments a part can be printed in ("PLA", "PETG", ...). Free text in an
array like ``tags`` rather than an enum, so the first request for a material
nobody thought of does not need a migration.

Existing rows land on the empty list, which means **not specified** — never
"any material": a part whose creator never said is not a part you may print in
anything, it is a part you should ask about.

Revision ID: 0048_resource_materials
Revises: 0047_request_item_priority
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0048_resource_materials"
down_revision: str | None = "0047_request_item_priority"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``materials``, defaulting existing rows to the empty list."""
    op.add_column(
        "resources",
        sa.Column(
            "materials",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    # The model owns the default for new rows (``default=list``), matching how
    # ``units``/``tags`` behave; the server_default exists only to backfill.
    op.alter_column("resources", "materials", server_default=None)


def downgrade() -> None:
    """Drop the materials column."""
    op.drop_column("resources", "materials")
