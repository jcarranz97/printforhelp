"""Add a priority (high/medium/low) to RequestItem.

Campaigns with many items need to tell the community which ones to print
first. ``priority`` is an ordering/attention hint only: it gates nothing, and
it is deliberately independent of ``status`` (open/fulfilled/closed) and of the
derived ``HelpState`` progress bucket.

Backfill: every existing item is stamped ``medium``, the default, so no
campaign's ordering changes until someone deliberately raises or lowers an
item. The ``server_default`` is dropped right after the backfill so new rows
fall back to the model-level default instead, matching how ``requests.status``
and ``requests.moderation_status`` are handled.

The enum's declaration order is NOT relied on for sorting — the service orders
via an explicit CASE (``PRIORITY_SORT_ORDER``) so adding a value later cannot
silently reshuffle every campaign.

Revision ID: 0047_request_item_priority
Revises: 0046_shipment_boxes
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0047_request_item_priority"
down_revision: str | None = "0046_shipment_boxes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ITEM_PRIORITY = sa.Enum("high", "medium", "low", name="request_item_priority")


def upgrade() -> None:
    """Add the priority column, stamping existing items as medium."""
    bind = op.get_bind()
    ITEM_PRIORITY.create(bind, checkfirst=True)

    op.add_column(
        "request_items",
        sa.Column(
            "priority",
            ITEM_PRIORITY,
            nullable=False,
            server_default="medium",
        ),
    )
    op.alter_column("request_items", "priority", server_default=None)
    op.create_index("ix_request_items_priority", "request_items", ["priority"])


def downgrade() -> None:
    """Drop the priority column and its enum type."""
    op.drop_index("ix_request_items_priority", table_name="request_items")
    op.drop_column("request_items", "priority")
    ITEM_PRIORITY.drop(op.get_bind(), checkfirst=True)
