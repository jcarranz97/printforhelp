"""Turn Shipments into trackable boxes: contents, relay hops, QR tokens.

Collection Centers pack many Contributions into one physical box and tape a
single QR on it. Some centers are relay hops (California collects, ships one
box to Texas, Texas nests several such boxes into a bigger one), so a box must
be able to contain other boxes as well as contributions.

Four schema moves:

1. Two new ``shipment_status`` values — ``in_transit`` and ``arrived``. Added
   with ``ADD VALUE`` (safe inside a transaction on PostgreSQL 12+ as long as
   the value is not *used* in the same transaction, which it is not here);
   every existing ``receiving``/``closed``/``cancelled`` row is untouched.

   .. warning::
      ``alembic/env.py`` wraps the **entire** ``upgrade head`` run in one
      transaction, so "not used in the same transaction" extends to every
      migration that runs after this one in the same invocation. A later
      revision that writes ``'in_transit'`` or ``'arrived'`` — a backfill,
      a seed — will fail with "unsafe use of new value". Split such a
      revision out, or swap the enum type instead of extending it.

2. ``shipments`` gains a scannable ``tracking_token``, a nullable
   ``destination_collection_center_id`` (set = this box is a relay hop to
   another center) and the dispatch/arrival stamps.
3. ``shipment_contents`` — the polymorphic manifest, holding either a tracking
   group (a Contribution) or a child shipment, never both. Soft-deleted on
   unpack so repacking is an append and the route history survives. The two
   partial unique indexes are the real invariant: a contribution — or a box —
   sits in exactly **one** open box at a time, which makes containment a
   forest and ancestor resolution unambiguous.
4. ``tracking_records`` gains ``shipment_id`` as a third polymorphic target so
   a box update lives on the same timeline as group and unit updates, and its
   exactly-one-target CHECK widens to a three-way sum.

Revision ID: 0046_shipment_boxes
Revises: 0045_tracking_item_seq
Create Date: 2026-07-25

"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0046_shipment_boxes"
down_revision: str | None = "0045_tracking_item_seq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ONE_TARGET_TWO = (
    "(tracking_group_id IS NOT NULL)::int + (tracking_item_id IS NOT NULL)::int = 1"
)
_ONE_TARGET_THREE = (
    "(tracking_group_id IS NOT NULL)::int "
    "+ (tracking_item_id IS NOT NULL)::int "
    "+ (shipment_id IS NOT NULL)::int = 1"
)


def upgrade() -> None:
    """Extend the status enum, the shipments table, and add the manifest."""
    _extend_status_enum()
    _extend_shipments()
    _create_shipment_contents()
    _extend_tracking_records()


def downgrade() -> None:
    """Reverse everything but the enum values (PostgreSQL cannot drop those)."""
    _revert_tracking_records()
    op.drop_table("shipment_contents")
    _revert_shipments()


def _extend_status_enum() -> None:
    """Add the transit states. ``IF NOT EXISTS`` keeps the step re-runnable."""
    for value in ("in_transit", "arrived"):
        op.execute(f"ALTER TYPE shipment_status ADD VALUE IF NOT EXISTS '{value}'")


def _extend_shipments() -> None:
    # Added nullable, backfilled, then tightened: every shipment owns a token
    # from birth, so nothing downstream has to handle a box that cannot be
    # scanned. Existing announcement-style rows simply gain a token nobody has
    # printed yet.
    op.add_column("shipments", sa.Column("tracking_token", sa.String(64)))
    bind = op.get_bind()
    for (shipment_id,) in bind.execute(sa.text("SELECT id FROM shipments")).all():
        bind.execute(
            sa.text("UPDATE shipments SET tracking_token = :token WHERE id = :id"),
            # Matches tracking.constants.TRACKING_TOKEN_BYTES; inlined because a
            # migration must not drift with application constants.
            {"token": secrets.token_urlsafe(16), "id": shipment_id},
        )
    op.alter_column("shipments", "tracking_token", nullable=False)
    op.create_index(
        "ix_shipments_tracking_token", "shipments", ["tracking_token"], unique=True
    )
    op.add_column(
        "shipments",
        sa.Column(
            "destination_collection_center_id",
            postgresql.UUID(as_uuid=True),
            # No CASCADE: archiving a center must not erase the shipments that
            # were routed through it.
            sa.ForeignKey("collection_centers.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_shipments_destination_cc", "shipments", ["destination_collection_center_id"]
    )
    op.add_column(
        "shipments", sa.Column("dispatched_at", sa.DateTime(timezone=True))
    )
    op.add_column("shipments", sa.Column("arrived_at", sa.DateTime(timezone=True)))
    op.add_column(
        "shipments",
        sa.Column(
            "arrived_by_id",
            postgresql.UUID(as_uuid=True),
            # No cascade from users (FR-013): who signed for the box outlives
            # their account being deactivated.
            sa.ForeignKey("users.id"),
        ),
    )


def _revert_shipments() -> None:
    op.drop_column("shipments", "arrived_by_id")
    op.drop_column("shipments", "arrived_at")
    op.drop_column("shipments", "dispatched_at")
    op.drop_index("ix_shipments_destination_cc", table_name="shipments")
    op.drop_column("shipments", "destination_collection_center_id")
    op.drop_index("ix_shipments_tracking_token", table_name="shipments")
    op.drop_column("shipments", "tracking_token")


def _create_shipment_contents() -> None:
    op.create_table(
        "shipment_contents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "shipment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shipments.id"),
            nullable=False,
        ),
        sa.Column(
            "tracking_group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracking_groups.id"),
            nullable=True,
        ),
        sa.Column(
            "child_shipment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shipments.id"),
            nullable=True,
        ),
        sa.Column(
            "added_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "removed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "(tracking_group_id IS NOT NULL)::int "
            "+ (child_shipment_id IS NOT NULL)::int = 1",
            name="shipment_content_one_target",
        ),
        sa.CheckConstraint(
            "child_shipment_id IS NULL OR child_shipment_id <> shipment_id",
            name="shipment_content_not_self",
        ),
    )
    # Partial on ``active``: a contribution (or a box) lives in exactly one
    # *open* box at a time, but keeps a row per box it has ever been packed
    # into, so "was in the California box, repacked into the Texas box" stays
    # queryable. A full unique constraint would forbid the second packing.
    op.create_index(
        "shipment_content_group_active",
        "shipment_contents",
        ["tracking_group_id"],
        unique=True,
        postgresql_where=sa.text("active AND tracking_group_id IS NOT NULL"),
    )
    op.create_index(
        "shipment_content_child_active",
        "shipment_contents",
        ["child_shipment_id"],
        unique=True,
        postgresql_where=sa.text("active AND child_shipment_id IS NOT NULL"),
    )
    op.create_index(
        "ix_shipment_contents_shipment",
        "shipment_contents",
        ["shipment_id"],
        postgresql_where=sa.text("active"),
    )


def _extend_tracking_records() -> None:
    op.add_column(
        "tracking_records",
        sa.Column(
            "shipment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shipments.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_tracking_records_shipment", "tracking_records", ["shipment_id"]
    )
    op.drop_constraint("tracking_record_one_target", "tracking_records", type_="check")
    op.create_check_constraint(
        "tracking_record_one_target", "tracking_records", _ONE_TARGET_THREE
    )


def _revert_tracking_records() -> None:
    op.drop_constraint("tracking_record_one_target", "tracking_records", type_="check")
    # Box updates have no home under the two-target CHECK, so a rollback drops
    # them. This is the one place the soft-delete rule cannot apply: the column
    # holding them is about to disappear.
    op.execute("DELETE FROM tracking_records WHERE shipment_id IS NOT NULL")
    op.create_check_constraint(
        "tracking_record_one_target", "tracking_records", _ONE_TARGET_TWO
    )
    op.drop_index("ix_tracking_records_shipment", table_name="tracking_records")
    op.drop_column("tracking_records", "shipment_id")
