"""Generalize the contribution ``printed`` state to ``prepared``.

Forward-compat for non-3D aid: a Contribution's middle lifecycle state
(the maker has produced/readied the item) is item-neutral, so the
print-specific ``printed`` is renamed to ``prepared``:

* the ``contribution_status`` enum value ``printed`` -> ``prepared``,
* the ``contributions.printed_at`` column -> ``prepared_at``.

The v1 UI still *displays* "printed" copy for 3D resources; only the
underlying state is neutral.

Revision ID: 0011_contribution_prepared
Revises: 0010_resources_generic
Create Date: 2026-06-28

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011_contribution_prepared"
down_revision: str | None = "0010_resources_generic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename the enum value and the timestamp column."""
    op.execute("ALTER TYPE contribution_status RENAME VALUE 'printed' TO 'prepared'")
    op.alter_column("contributions", "printed_at", new_column_name="prepared_at")


def downgrade() -> None:
    """Reverse the rename."""
    op.alter_column("contributions", "prepared_at", new_column_name="printed_at")
    op.execute("ALTER TYPE contribution_status RENAME VALUE 'prepared' TO 'printed'")
