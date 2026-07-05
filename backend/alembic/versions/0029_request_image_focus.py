"""Add a focal point to request cover images.

Lets the requester choose which part of a cover image stays visible when
the banner crops it (CSS ``object-position``), so tall posters are not
arbitrarily cropped through their center. Percent coordinates (0-100),
defaulting to the center (50, 50).

Revision ID: 0029_request_image_focus
Revises: 0028_username_chosen
Create Date: 2026-07-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_request_image_focus"
down_revision: str | None = "0028_username_chosen"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``image_focus_x`` / ``image_focus_y`` columns to requests."""
    op.add_column(
        "requests",
        sa.Column(
            "image_focus_x",
            sa.Float(),
            nullable=False,
            server_default="50",
        ),
    )
    op.add_column(
        "requests",
        sa.Column(
            "image_focus_y",
            sa.Float(),
            nullable=False,
            server_default="50",
        ),
    )


def downgrade() -> None:
    """Drop the focal-point columns from requests."""
    op.drop_column("requests", "image_focus_y")
    op.drop_column("requests", "image_focus_x")
