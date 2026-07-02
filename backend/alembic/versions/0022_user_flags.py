"""Add a generic per-user flags table (traits + capabilities).

Stores yes/no attributes attached to users (e.g. the self-declared ``maker``
trait, and later admin-granted capabilities like ``can_add_part``). One row per
``(user_id, key)``; the absence of a row means "unknown". See
``app/users/flags.py`` for the registry and trust model.

Revision ID: 0022_user_flags
Revises: 0021_request_item_number
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0022_user_flags"
down_revision: str | None = "0021_request_item_number"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    ]


def upgrade() -> None:
    op.create_table(
        "user_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "set_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        *_timestamps(),
        sa.UniqueConstraint("user_id", "key", name="uq_user_flag_key"),
    )
    op.create_index("ix_user_flags_user_id", "user_flags", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_flags_user_id", table_name="user_flags")
    op.drop_table("user_flags")
