"""Add users.google_sub for "Sign in with Google".

Links a user account to a Google account by its stable subject id. Nullable
and unique; only set for users who signed in with Google.

Revision ID: 0027_user_google_sub
Revises: 0026_password_reset_tokens
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027_user_google_sub"
down_revision: str | None = "0026_password_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("google_sub", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
