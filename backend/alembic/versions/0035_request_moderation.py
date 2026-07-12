"""Add the Request moderation (publication) gate.

Campaigns now go draft -> pending -> approved | changes_requested | rejected
(FR-134). Only ``approved`` is public; everything else is visible solely to the
campaign's requesters and to maintainers/admins.

``moderation_status`` is deliberately a SEPARATE column from ``status``: that
one is the campaign lifecycle (open/fulfilled/closed), is guarded by the
``request_closed_consistency`` CHECK, and feeds the HelpState progress math.

Backfill: every campaign that exists today is already publicly listed, so it is
stamped ``approved`` — this migration must not retroactively hide live
campaigns. New rows default to ``draft`` at the application level.

Revision ID: 0035_request_moderation
Revises: 0034_resource_labels_pp
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0035_request_moderation"
down_revision: str | None = "0034_resource_labels_pp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODERATION_STATUS = sa.Enum(
    "draft",
    "pending",
    "changes_requested",
    "approved",
    "rejected",
    name="request_moderation_status",
)


def upgrade() -> None:
    """Add the moderation columns; stamp existing campaigns as approved."""
    bind = op.get_bind()
    MODERATION_STATUS.create(bind, checkfirst=True)

    # Added nullable + server_default 'approved' so the backfill of existing
    # rows is atomic with the DDL; the default is dropped immediately after so
    # new rows fall back to the model's ``draft`` default instead.
    op.add_column(
        "requests",
        sa.Column(
            "moderation_status",
            MODERATION_STATUS,
            nullable=False,
            server_default="approved",
        ),
    )
    op.alter_column("requests", "moderation_status", server_default=None)
    op.create_index(
        "ix_requests_moderation_status", "requests", ["moderation_status"]
    )

    op.add_column(
        "requests",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("requests", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column(
        "requests",
        sa.Column(
            "reviewed_by_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "requests",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Existing campaigns were public before this migration and stay public;
    # treat their creation as the moment they were "approved".
    op.execute(
        "UPDATE requests SET submitted_at = created_at, reviewed_at = created_at"
    )


def downgrade() -> None:
    """Drop the moderation columns and the enum type."""
    op.drop_column("requests", "reviewed_at")
    op.drop_column("requests", "reviewed_by_id")
    op.drop_column("requests", "review_note")
    op.drop_column("requests", "submitted_at")
    op.drop_index("ix_requests_moderation_status", table_name="requests")
    op.drop_column("requests", "moderation_status")
    MODERATION_STATUS.drop(op.get_bind(), checkfirst=True)
