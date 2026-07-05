"""Add a focal point to Resource (part) images.

Lets the owner choose which part of a part's image stays visible when a
fixed-aspect box crops it (CSS ``object-position``), mirroring the request
cover feature. Percent coordinates (0-100), defaulting to the center
(50, 50).

Revision ID: 0030_resource_image_focus
Revises: 0029_request_image_focus
Create Date: 2026-07-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_resource_image_focus"
down_revision: str | None = "0029_request_image_focus"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``image_focus_x`` / ``image_focus_y`` columns to resources."""
    op.add_column(
        "resources",
        sa.Column(
            "image_focus_x",
            sa.Float(),
            nullable=False,
            server_default="50",
        ),
    )
    op.add_column(
        "resources",
        sa.Column(
            "image_focus_y",
            sa.Float(),
            nullable=False,
            server_default="50",
        ),
    )


def downgrade() -> None:
    """Drop the focal-point columns from resources."""
    op.drop_column("resources", "image_focus_y")
    op.drop_column("resources", "image_focus_x")
