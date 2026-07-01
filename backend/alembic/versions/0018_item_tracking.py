"""Add item-tracking (QR provenance) tables.

Introduces the maker-facing item tracking feature:

- ``tracking_groups`` — one per Contribution (unique), holding the group
  ``tracking_token`` and the private/group/public ``visibility`` tier.
- ``tracking_items`` — one per printed unit, each with its own token and a
  1-based ``sequence`` within the group.
- ``tracking_group_members`` — named users granted read access under the
  ``group`` visibility tier (no cascade from users, FR-013).
- ``tracking_records`` — the timeline entries, polymorphic to a group *or*
  an item (XOR check), with a nullable ``author_user_id`` (recorded even when
  ``display_anonymous`` hides it from the public timeline) and ``tags``.

Revision ID: 0018_item_tracking
Revises: 0017_notifications
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0018_item_tracking"
down_revision: str | None = "0017_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def upgrade() -> None:
    """Create the tracking enum and four tables."""
    visibility = postgresql.ENUM(
        "private", "group", "public", name="tracking_visibility"
    )
    visibility.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tracking_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contribution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contributions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("tracking_token", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "visibility",
            postgresql.ENUM(name="tracking_visibility", create_type=False),
            nullable=False,
            server_default="private",
        ),
        *_timestamps(),
    )
    op.create_index(
        "ix_tracking_groups_contribution_id", "tracking_groups", ["contribution_id"]
    )
    op.create_index(
        "ix_tracking_groups_tracking_token", "tracking_groups", ["tracking_token"]
    )

    op.create_table(
        "tracking_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracking_groups.id"),
            nullable=False,
        ),
        sa.Column("tracking_token", sa.String(64), nullable=False, unique=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint(
            "group_id", "sequence", name="tracking_item_group_sequence"
        ),
    )
    op.create_index("ix_tracking_items_group_id", "tracking_items", ["group_id"])
    op.create_index(
        "ix_tracking_items_tracking_token", "tracking_items", ["tracking_token"]
    )

    op.create_table(
        "tracking_group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracking_groups.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        *_timestamps(),
        sa.UniqueConstraint("group_id", "user_id", name="tracking_group_member_unique"),
    )
    op.create_index(
        "ix_tracking_group_members_group_id", "tracking_group_members", ["group_id"]
    )
    op.create_index(
        "ix_tracking_group_members_user_id", "tracking_group_members", ["user_id"]
    )

    op.create_table(
        "tracking_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tracking_group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracking_groups.id"),
            nullable=True,
        ),
        sa.Column(
            "tracking_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracking_items.id"),
            nullable=True,
        ),
        sa.Column(
            "author_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "display_anonymous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "(tracking_group_id IS NOT NULL)::int "
            "+ (tracking_item_id IS NOT NULL)::int = 1",
            name="tracking_record_one_target",
        ),
    )
    op.create_index(
        "ix_tracking_records_tracking_group_id",
        "tracking_records",
        ["tracking_group_id"],
    )
    op.create_index(
        "ix_tracking_records_tracking_item_id",
        "tracking_records",
        ["tracking_item_id"],
    )


def downgrade() -> None:
    """Drop the tracking tables and enum."""
    op.drop_table("tracking_records")
    op.drop_table("tracking_group_members")
    op.drop_table("tracking_items")
    op.drop_table("tracking_groups")
    postgresql.ENUM(name="tracking_visibility").drop(op.get_bind(), checkfirst=True)
