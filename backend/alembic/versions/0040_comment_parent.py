"""Add ``parent_comment_id`` to comments for single-level replies.

A nullable self-referential foreign key on ``comments`` lets a comment be a
reply to a top-level comment (Instagram-style). Replies never nest deeper than
one level — the service re-roots a reply-to-a-reply onto the top-level comment
— so this one column is all the schema needs. A supporting index speeds the
"fetch a comment's replies" read.

Revision ID: 0040_comment_parent
Revises: 0039_reactions
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0040_comment_parent"
down_revision: str | None = "0039_reactions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable parent self-FK and its index."""
    op.add_column(
        "comments",
        sa.Column(
            "parent_comment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("comments.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_comments_parent_created",
        "comments",
        ["parent_comment_id", "created_at"],
    )


def downgrade() -> None:
    """Drop the reply index and the parent column."""
    op.drop_index("ix_comments_parent_created", table_name="comments")
    op.drop_column("comments", "parent_comment_id")
