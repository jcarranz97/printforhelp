"""Make ``tracking_items(group_id, sequence)`` unique only among live units.

A maintainer correcting a Contribution's unit count downwards retires the
surplus tracking items (``active = false``) instead of deleting them, so their
scan history survives. Growing the count back must then mint a **new** row —
and a **new** token — for the same sequence, because the label printed for the
old one was thrown away with the units that never arrived.

The original full unique constraint made that impossible (one row per
``(group, sequence)``, ever), forcing a regrow to resurrect the old token. The
partial index keeps the real invariant — *at most one live unit per sequence
per group* — while letting any number of retired rows share it.

Revision ID: 0045_tracking_item_seq
Revises: 0044_username_change_hidden
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0045_tracking_item_seq"
down_revision: str | None = "0044_username_change_hidden"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Swap the full unique constraint for one partial to ``active`` rows."""
    op.drop_constraint(
        "tracking_item_group_sequence", "tracking_items", type_="unique"
    )
    op.create_index(
        "tracking_item_group_sequence_active",
        "tracking_items",
        ["group_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("active"),
    )


def downgrade() -> None:
    """Restore the full unique constraint.

    Only reversible while no group has retired *and* re-grown a sequence; once
    two rows share one ``(group_id, sequence)``, the old constraint cannot be
    recreated and this fails loudly rather than dropping rows.
    """
    op.drop_index("tracking_item_group_sequence_active", table_name="tracking_items")
    op.create_unique_constraint(
        "tracking_item_group_sequence", "tracking_items", ["group_id", "sequence"]
    )
