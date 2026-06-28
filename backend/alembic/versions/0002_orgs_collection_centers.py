"""Organizations and Collection Centers (Phase 2).

Adds the ``organizations``, ``organization_memberships``,
``collection_centers``, and ``collection_center_memberships`` tables,
their enum types, polymorphic-ownership CHECK constraints, and the
partial unique indexes that enforce single-active invariants.

Revision ID: 0002_orgs_cc
Revises: 0001_initial
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_orgs_cc"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create enums and the Phase 2 tables with their indexes."""
    organization_status = postgresql.ENUM(
        "active", "inactive", name="organization_status"
    )
    organization_role = postgresql.ENUM(
        "owner", "member", name="organization_role"
    )
    collection_center_status = postgresql.ENUM(
        "active", "inactive", name="collection_center_status"
    )
    collection_center_role = postgresql.ENUM(
        "contributor", name="collection_center_role"
    )
    bind = op.get_bind()
    organization_status.create(bind, checkfirst=True)
    organization_role.create(bind, checkfirst=True)
    collection_center_status.create(bind, checkfirst=True)
    collection_center_role.create(bind, checkfirst=True)

    _create_organizations()
    _create_organization_memberships()
    _create_collection_centers()
    _create_collection_center_memberships()


def _create_organizations() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact", sa.String(255), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("country", sa.String(80), nullable=False),
        sa.Column(
            "verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "registered_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "verified_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="organization_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
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
        sa.UniqueConstraint("name", name="uq_organizations_name"),
        sa.CheckConstraint(
            "(verified = FALSE) OR (verified_by_id IS NOT NULL)",
            name="verified_implies_verifier",
        ),
    )
    op.create_index("idx_organizations_name", "organizations", ["name"])
    op.create_index("idx_organizations_country", "organizations", ["country"])
    op.create_index("idx_organizations_verified", "organizations", ["verified"])
    op.create_index("idx_organizations_status", "organizations", ["status"])
    op.create_index("idx_organizations_active", "organizations", ["active"])


def _create_organization_memberships() -> None:
    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM(name="organization_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "invited_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
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
    )
    op.create_index(
        "uniq_org_membership_active",
        "organization_memberships",
        ["organization_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("active = TRUE"),
    )
    op.create_index(
        "uniq_org_owner_active",
        "organization_memberships",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("active = TRUE AND role = 'owner'"),
    )
    op.create_index(
        "idx_org_membership_user", "organization_memberships", ["user_id"]
    )
    op.create_index(
        "idx_org_membership_org",
        "organization_memberships",
        ["organization_id"],
    )


def _create_collection_centers() -> None:
    op.create_table(
        "collection_centers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("country", sa.String(80), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("contact", sa.String(255), nullable=False),
        sa.Column("opening_hours", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "registered_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "verified_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
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
        sa.Column(
            "status",
            postgresql.ENUM(name="collection_center_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
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
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_organization_id IS NULL) OR "
            "(owner_user_id IS NULL AND owner_organization_id IS NOT NULL)",
            name="cc_one_owner",
        ),
        sa.CheckConstraint(
            "(verified = FALSE) OR (verified_by_id IS NOT NULL)",
            name="cc_verified_implies_verifier",
        ),
    )
    op.create_index("idx_cc_verified", "collection_centers", ["verified"])
    op.create_index("idx_cc_status", "collection_centers", ["status"])
    op.create_index("idx_cc_active", "collection_centers", ["active"])
    op.create_index(
        "idx_cc_country_city", "collection_centers", ["country", "city"]
    )
    op.create_index(
        "idx_cc_owner_user", "collection_centers", ["owner_user_id"]
    )
    op.create_index(
        "idx_cc_owner_org", "collection_centers", ["owner_organization_id"]
    )


def _create_collection_center_memberships() -> None:
    op.create_table(
        "collection_center_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "collection_center_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("collection_centers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM(name="collection_center_role", create_type=False),
            nullable=False,
            server_default="contributor",
        ),
        sa.Column(
            "invited_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
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
    )
    op.create_index(
        "uniq_cc_membership_active",
        "collection_center_memberships",
        ["collection_center_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("active = TRUE"),
    )
    op.create_index(
        "idx_cc_membership_user",
        "collection_center_memberships",
        ["user_id"],
    )
    op.create_index(
        "idx_cc_membership_cc",
        "collection_center_memberships",
        ["collection_center_id"],
    )


def downgrade() -> None:
    """Drop the Phase 2 tables and their enum types."""
    op.drop_table("collection_center_memberships")
    op.drop_table("collection_centers")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
    for enum_name in (
        "collection_center_role",
        "collection_center_status",
        "organization_role",
        "organization_status",
    ):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
