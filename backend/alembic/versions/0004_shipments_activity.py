"""Shipments, public activity log, and comments (Phase 3).

Adds the ``shipments`` table (with the ``shipment_status`` enum) plus the
polymorphic ``activity_log`` and ``comments`` tables that power the public
timeline and Markdown comments on Collection Centers and Shipments.

Revision ID: 0004_shipments_activity
Revises: 0003_user_email
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_shipments_activity"
down_revision: str | None = "0003_user_email"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the shipment enum and the three Phase 3 tables."""
    shipment_status = postgresql.ENUM(
        "receiving", "closed", "cancelled", name="shipment_status"
    )
    shipment_status.create(op.get_bind(), checkfirst=True)

    _create_shipments()
    _create_activity_log()
    _create_comments()


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
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
    ]


def _create_shipments() -> None:
    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "collection_center_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("collection_centers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("shipment_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="shipment_status", create_type=False),
            nullable=False,
            server_default="receiving",
        ),
        sa.Column("destination", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        *_timestamps(),
    )
    op.create_index("ix_shipments_cc", "shipments", ["collection_center_id"])
    op.create_index("ix_shipments_date", "shipments", ["shipment_date"])
    op.create_index("ix_shipments_status", "shipments", ["status"])


def _create_activity_log() -> None:
    op.create_table(
        "activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column(
            "changes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        *_timestamps(),
    )
    op.create_index(
        "ix_activity_log_entity_created",
        "activity_log",
        ["entity_type", "entity_id", "created_at"],
    )


def _create_comments() -> None:
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "author_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "ix_comments_entity_created",
        "comments",
        ["entity_type", "entity_id", "created_at"],
    )


def downgrade() -> None:
    """Drop the Phase 3 tables and the shipment enum."""
    op.drop_table("comments")
    op.drop_table("activity_log")
    op.drop_table("shipments")
    postgresql.ENUM(name="shipment_status").drop(op.get_bind(), checkfirst=True)
