"""Link a tracking record back to the box comment that produced it.

A comment posted on a box is mirrored onto that box's tracking timeline so it
waterfalls down onto every package and unit inside — that is how a maker who
only ever scans their own QR hears what happened to the box carrying it. The
mirror needs a way home: without it an edited comment would drift from its
copy, and a deleted one would live on across every track page it reached.

Nullable, because every record posted directly on a QR has no comment behind
it. ``ondelete`` is deliberately absent: comments are soft-deleted like
everything else, so the row never actually goes away.

Revision ID: 0049_tracking_record_comment
Revises: 0048_resource_materials
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0049_tracking_record_comment"
down_revision: str | None = "0048_resource_materials"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``comment_id`` back-reference and its index."""
    op.add_column(
        "tracking_records",
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "tracking_records_comment_id_fkey",
        "tracking_records",
        "comments",
        ["comment_id"],
        ["id"],
    )
    op.create_index(
        "ix_tracking_records_comment_id", "tracking_records", ["comment_id"]
    )


def downgrade() -> None:
    """Drop the back-reference."""
    op.drop_index("ix_tracking_records_comment_id", table_name="tracking_records")
    op.drop_constraint(
        "tracking_records_comment_id_fkey", "tracking_records", type_="foreignkey"
    )
    op.drop_column("tracking_records", "comment_id")
