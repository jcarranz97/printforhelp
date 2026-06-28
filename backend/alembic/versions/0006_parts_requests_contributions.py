"""Parts catalog, Requests/RequestItems, and Contributions (Phase 4).

Adds the ``parts``, ``requests``, ``request_items``, and ``contributions``
tables with their enums (``part_status``, ``request_status``,
``contribution_status``), polymorphic-owner / requester CHECK constraints,
and supporting indexes.

Revision ID: 0006_parts_requests
Revises: 0005_cc_location_url
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_parts_requests"
down_revision: str | None = "0005_cc_location_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the Phase 4 enums and four tables."""
    part_status = postgresql.ENUM("active", "discontinued", name="part_status")
    request_status = postgresql.ENUM(
        "open", "fulfilled", "closed", name="request_status"
    )
    contribution_status = postgresql.ENUM(
        "claimed", "printed", "delivered", "received", "released",
        name="contribution_status",
    )
    bind = op.get_bind()
    part_status.create(bind, checkfirst=True)
    request_status.create(bind, checkfirst=True)
    contribution_status.create(bind, checkfirst=True)

    _create_parts()
    _create_requests()
    _create_request_items()
    _create_contributions()


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def _create_parts() -> None:
    op.create_table(
        "parts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="part_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "featured", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "owner_organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_organization_id IS NULL) OR "
            "(owner_user_id IS NULL AND owner_organization_id IS NOT NULL)",
            name="parts_one_owner",
        ),
        *_timestamps(),
    )
    op.create_index("ix_parts_status", "parts", ["status"])
    op.create_index("ix_parts_featured", "parts", ["featured"])
    op.create_index("ix_parts_owner_user", "parts", ["owner_user_id"])
    op.create_index("ix_parts_owner_org", "parts", ["owner_organization_id"])


def _create_requests() -> None:
    op.create_table(
        "requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column(
            "requester_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "requester_organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "preferred_collection_center_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="request_status", create_type=False),
            nullable=False,
            server_default="open",
        ),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        sa.Column(
            "closed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(requester_user_id IS NOT NULL AND requester_organization_id IS NULL) "
            "OR (requester_user_id IS NULL "
            "AND requester_organization_id IS NOT NULL)",
            name="requests_one_requester",
        ),
        sa.CheckConstraint(
            "(status = 'open' AND closed_at IS NULL) OR "
            "(status IN ('fulfilled', 'closed') AND closed_at IS NOT NULL)",
            name="request_closed_consistency",
        ),
        *_timestamps(),
    )
    op.create_index("ix_requests_status", "requests", ["status"])
    op.create_index("ix_requests_requester_user", "requests", ["requester_user_id"])
    op.create_index(
        "ix_requests_requester_org", "requests", ["requester_organization_id"]
    )


def _create_request_items() -> None:
    op.create_table(
        "request_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "part_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("parts.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="request_status", create_type=False),
            nullable=False,
            server_default="open",
        ),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        sa.Column(
            "closed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="request_item_quantity_positive",
        ),
        sa.CheckConstraint(
            "(status = 'open' AND closed_at IS NULL) OR "
            "(status IN ('fulfilled', 'closed') AND closed_at IS NOT NULL)",
            name="request_item_closed_consistency",
        ),
        *_timestamps(),
    )
    op.create_index("ix_request_items_request", "request_items", ["request_id"])
    op.create_index("ix_request_items_part", "request_items", ["part_id"])
    op.create_index("ix_request_items_status", "request_items", ["status"])


def _create_contributions() -> None:
    op.create_table(
        "contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("request_items.id"),
            nullable=False,
        ),
        sa.Column(
            "maker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "collection_center_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("collection_centers.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="contribution_status", create_type=False),
            nullable=False,
            server_default="claimed",
        ),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("printed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "received_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "auto_received", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_reason", sa.String(64), nullable=True),
        sa.CheckConstraint(
            "quantity > 0", name="contribution_quantity_positive"
        ),
        *_timestamps(),
    )
    op.create_index(
        "ix_contributions_item", "contributions", ["request_item_id"]
    )
    op.create_index("ix_contributions_maker", "contributions", ["maker_id"])
    op.create_index(
        "ix_contributions_center", "contributions", ["collection_center_id"]
    )
    op.create_index("ix_contributions_status", "contributions", ["status"])


def downgrade() -> None:
    """Drop the Phase 4 tables and enums."""
    op.drop_table("contributions")
    op.drop_table("request_items")
    op.drop_table("requests")
    op.drop_table("parts")
    bind = op.get_bind()
    postgresql.ENUM(name="contribution_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="request_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="part_status").drop(bind, checkfirst=True)
