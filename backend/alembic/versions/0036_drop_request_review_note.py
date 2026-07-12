"""Drop ``requests.review_note``.

The one-shot review note was superseded by the private ``request_review``
comment thread (FR-136), where the reviewer explains and the author can
actually reply. Keeping the column would leave a second, mute source of truth
for the same thing — and the UI was showing both.

Any text still sitting in the column is dropped: the review conversation is the
record now, and the audit log already carries the transitions.

Revision ID: 0036_drop_review_note
Revises: 0035_request_moderation
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036_drop_review_note"
down_revision: str | None = "0035_request_moderation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the superseded one-shot review note column."""
    op.drop_column("requests", "review_note")


def downgrade() -> None:
    """Restore the column (empty — the original notes are not recoverable)."""
    op.add_column("requests", sa.Column("review_note", sa.Text(), nullable=True))
