"""Add watch subscriptions and in-app notifications.

Introduces two polymorphic tables (mirroring the activity log's
``entity_type`` + ``entity_id`` shape):

- ``watches`` — a user's subscription to an entity. Unwatch is a soft
  delete; a partial unique index keeps at most one active row per
  (user, entity).
- ``notifications`` — one row per recipient, fanned out when a watched
  entity sees activity or when the user is @mentioned in a comment.

``reason``/``event`` and the nullable ``emailed_at`` column are forward
hooks for a future opt-in email digest (in-app only in v1).

Revision ID: 0017_notifications
Revises: 0016_notice_severity_success
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_notifications"
down_revision: str | None = "0016_notice_severity_success"
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
    """Create the watches and notifications tables."""
    op.create_table(
        "watches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_watches_user_id", "watches", ["user_id"])
    op.create_index("ix_watches_entity", "watches", ["entity_type", "entity_id"])
    op.create_index(
        "uq_watches_active",
        "watches",
        ["user_id", "entity_type", "entity_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recipient_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "ix_notifications_recipient_user_id",
        "notifications",
        ["recipient_user_id"],
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["recipient_user_id", "read_at", "created_at"],
    )


def downgrade() -> None:
    """Drop the notifications and watches tables."""
    op.drop_table("notifications")
    op.drop_table("watches")
