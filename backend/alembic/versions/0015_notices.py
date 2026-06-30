"""Add site notices (page banners + per-entity notices) and translations.

Introduces the ``notices`` table and its per-language ``notice_translations``
child. A notice is in exactly one mode (page ``scopes`` XOR an entity
``target_type`` + ``target_id``) and carries an approval ``status`` so owner
requests can be moderated before they show. Localized title/message live in
the child table so new languages need no migration.

Revision ID: 0015_notices
Revises: 0014_contribution_tags
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_notices"
down_revision: str | None = "0014_contribution_tags"
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
    """Create the notice enums and the two notice tables."""
    notice_severity = postgresql.ENUM(
        "info", "warning", "critical", name="notice_severity"
    )
    notice_status = postgresql.ENUM(
        "pending", "approved", "declined", name="notice_status"
    )
    bind = op.get_bind()
    notice_severity.create(bind, checkfirst=True)
    notice_status.create(bind, checkfirst=True)

    op.create_table(
        "notices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "severity",
            postgresql.ENUM(name="notice_severity", create_type=False),
            nullable=False,
            server_default="info",
        ),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="notice_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("decline_reason", sa.Text(), nullable=True),
        sa.Column(
            "requested_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "approved_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(target_type IS NOT NULL AND target_id IS NOT NULL "
            "AND cardinality(scopes) = 0) OR "
            "(target_type IS NULL AND target_id IS NULL "
            "AND cardinality(scopes) > 0)",
            name="notice_one_mode",
        ),
        sa.CheckConstraint(
            "(status != 'approved') OR (approved_by_id IS NOT NULL)",
            name="notice_approved_implies_approver",
        ),
        *_timestamps(),
    )
    op.create_index("ix_notices_severity", "notices", ["severity"])
    op.create_index("ix_notices_status", "notices", ["status"])
    op.create_index("ix_notices_target_type", "notices", ["target_type"])
    op.create_index("ix_notices_target_id", "notices", ["target_id"])

    op.create_table(
        "notice_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("action_label", sa.Text(), nullable=True),
        sa.Column("action_url", sa.Text(), nullable=True),
        sa.UniqueConstraint("notice_id", "language", name="uq_notice_translation_lang"),
        sa.CheckConstraint(
            "(action_url IS NULL) = (action_label IS NULL)",
            name="notice_translation_action_pairing",
        ),
        *_timestamps(),
    )
    op.create_index(
        "ix_notice_translations_notice", "notice_translations", ["notice_id"]
    )


def downgrade() -> None:
    """Drop the notice tables and enums."""
    op.drop_table("notice_translations")
    op.drop_table("notices")
    bind = op.get_bind()
    postgresql.ENUM(name="notice_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="notice_severity").drop(bind, checkfirst=True)
