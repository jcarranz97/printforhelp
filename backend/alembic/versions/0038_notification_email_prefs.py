"""Add notification preferences and the email outbox.

Two tables that turn the in-app-only notification system into a
multi-channel one:

- ``notification_preferences`` — one row per ``(user, category)`` with an
  in-app and an email toggle. Absent row means the category default applies.
- ``notification_email_outbox`` — the transactional outbox. A row is written
  in the same transaction as the notification when the recipient wants email,
  then a background worker drains it (``FOR UPDATE SKIP LOCKED``), sends over
  SMTP, and stamps ``sent_at``.

Revision ID: 0038_notification_email_prefs
Revises: 0037_resource_packaging
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0038_notification_email_prefs"
down_revision: str | None = "0037_resource_packaging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the preferences and email-outbox tables."""
    op.create_table(
        "notification_preferences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
    )
    op.create_index(
        "uq_notification_preferences_active",
        "notification_preferences",
        ["user_id", "category"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    op.create_table(
        "notification_email_outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
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
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_notification_email_outbox_recipient_user_id",
        "notification_email_outbox",
        ["recipient_user_id"],
    )
    op.create_index(
        "ix_notification_email_outbox_pending",
        "notification_email_outbox",
        ["sent_at", "active"],
    )


def downgrade() -> None:
    """Drop the email-outbox and preferences tables."""
    op.drop_index(
        "ix_notification_email_outbox_pending",
        table_name="notification_email_outbox",
    )
    op.drop_index(
        "ix_notification_email_outbox_recipient_user_id",
        table_name="notification_email_outbox",
    )
    op.drop_table("notification_email_outbox")
    op.drop_index(
        "uq_notification_preferences_active",
        table_name="notification_preferences",
    )
    op.drop_index(
        "ix_notification_preferences_user_id",
        table_name="notification_preferences",
    )
    op.drop_table("notification_preferences")
