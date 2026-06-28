"""Add email + full_name to users for self-registration (FR-001).

Both columns are nullable: accounts that predate self-registration
(admin, anonymous, admin-provisioned users) keep ``email = NULL`` and log
in by username. Self-registered users always set both columns. ``email``
is unique so it can serve as a login identifier.

Revision ID: 0003_user_email
Revises: 0002_orgs_cc
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_user_email"
down_revision: str | None = "0002_orgs_cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``email`` and ``full_name`` columns to ``users``."""
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column(
        "users", sa.Column("full_name", sa.String(255), nullable=True)
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    """Drop the ``email`` and ``full_name`` columns from ``users``."""
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "full_name")
    op.drop_column("users", "email")
