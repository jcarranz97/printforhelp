"""Let maintainers hide a username change from the public timeline.

A rename that reveals an old email-as-handle can now be hidden by a
maintainer/admin. Hidden rows stay in the history (the rename cooldown reads
``active``, which is left untouched) but are shown only to maintainers/admins.

Revision ID: 0044_username_change_hidden
Revises: 0043_username_changes
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0044_username_change_hidden"
down_revision: str | None = "0043_username_changes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``hidden`` flag to ``username_changes`` (default false)."""
    op.add_column(
        "username_changes",
        sa.Column(
            "hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Drop the ``hidden`` flag."""
    op.drop_column("username_changes", "hidden")
