"""Add the password_reset_tokens table for the forgot-password flow.

Stores a SHA-256 hash of each one-time reset token (never the raw value),
plus its expiry and a ``used_at`` stamp once redeemed.

Revision ID: 0026_password_reset_tokens
Revises: 0025_cc_listed
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0026_password_reset_tokens"
down_revision: str | None = "0025_cc_listed"
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
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"]
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_tokens_token_hash", table_name="password_reset_tokens"
    )
    op.drop_index(
        "ix_password_reset_tokens_user_id", table_name="password_reset_tokens"
    )
    op.drop_table("password_reset_tokens")
