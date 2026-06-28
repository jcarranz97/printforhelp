"""Rename collection_centers.notes to description (Markdown).

The center "notes" field is repurposed as a Markdown ``description`` that
the frontend renders (and effective members / maintainers can edit),
aligning Collection Centers with Parts and Requests.

Revision ID: 0007_cc_description
Revises: 0006_parts_requests
Create Date: 2026-06-28

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_cc_description"
down_revision: str | None = "0006_parts_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename the ``notes`` column to ``description``."""
    op.alter_column(
        "collection_centers", "notes", new_column_name="description"
    )


def downgrade() -> None:
    """Restore the original ``notes`` column name."""
    op.alter_column(
        "collection_centers", "description", new_column_name="notes"
    )
