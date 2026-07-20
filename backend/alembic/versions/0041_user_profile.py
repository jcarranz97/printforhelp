"""Add public-profile fields to users.

Adds two nullable columns backing the public user profile page: ``avatar_url``
(a stored upload URL rendered as the circular avatar everywhere the user
appears) and ``bio`` (a short self-authored blurb). Both nullable so existing
accounts are unaffected and fall back to their initials / no blurb.

Revision ID: 0041_user_profile
Revises: 0040_comment_parent
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0041_user_profile"
down_revision: str | None = "0040_comment_parent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable ``avatar_url`` and ``bio`` columns to users."""
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(length=280), nullable=True))


def downgrade() -> None:
    """Drop the ``avatar_url`` and ``bio`` columns from users."""
    op.drop_column("users", "bio")
    op.drop_column("users", "avatar_url")
