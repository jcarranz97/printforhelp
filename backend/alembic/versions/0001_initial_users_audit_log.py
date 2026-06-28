"""Initial schema: users and audit_log (Phase 1).

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create enum types, the users table, and the audit_log table."""
    user_role = postgresql.ENUM(
        "user", "maintainer", "admin", name="user_role"
    )
    locale_code = postgresql.ENUM("es", "en", name="locale_code")
    user_role.create(op.get_bind(), checkfirst=True)
    locale_code.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(name="user_role", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "preferred_locale",
            postgresql.ENUM(name="locale_code", create_type=False),
            nullable=False,
            server_default="es",
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
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("idx_users_username", "users", ["username"])
    op.create_index("idx_users_active", "users", ["active"])
    op.create_index("idx_users_role", "users", ["role"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_audit_actor_created",
        "audit_log",
        ["actor_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_audit_target_created",
        "audit_log",
        ["target_type", "target_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_audit_action_created",
        "audit_log",
        ["action", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """Drop the audit_log and users tables and their enum types."""
    op.drop_table("audit_log")
    op.drop_table("users")
    postgresql.ENUM(name="locale_code").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
