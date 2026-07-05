"""Add users.username_chosen for the Google username-onboarding step.

False only for freshly-created Google accounts that still carry an
auto-generated username and must pick their own. Existing rows (and all
non-Google accounts) default to True.

Revision ID: 0028_username_chosen
Revises: 0027_user_google_sub
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028_username_chosen"
down_revision: str | None = "0027_user_google_sub"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "username_chosen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "username_chosen")
