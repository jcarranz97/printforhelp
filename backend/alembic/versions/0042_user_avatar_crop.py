"""Add an avatar crop rectangle to users.

Lets a user choose exactly which part of their picture becomes the circular
avatar — both *where* (pan) and *how much* (zoom). Stored as the crop's
position and size in **percent of the source image**, which is resolution- and
container-independent: the same four numbers render the identical crop at every
avatar size (32px in the nav, 224px on the profile).

A focal point alone could only pan, never zoom, which is why this supersedes
that approach. The default 0/0/100/100 means "no crop chosen"; the frontend
falls back to a centred ``object-fit: cover`` for those, so an avatar set
without a crop is never distorted.

Revision ID: 0042_user_avatar_crop
Revises: 0041_user_profile
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0042_user_avatar_crop"
down_revision: str | None = "0041_user_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = {
    "avatar_crop_x": "0",
    "avatar_crop_y": "0",
    "avatar_crop_w": "100",
    "avatar_crop_h": "100",
}


def upgrade() -> None:
    """Add the avatar crop-rectangle columns to users."""
    for name, default in _COLUMNS.items():
        op.add_column(
            "users",
            sa.Column(name, sa.Float(), nullable=False, server_default=default),
        )


def downgrade() -> None:
    """Drop the avatar crop-rectangle columns from users."""
    for name in reversed(list(_COLUMNS)):
        op.drop_column("users", name)
