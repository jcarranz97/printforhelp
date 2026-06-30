"""Add a ``success`` value to the notice_severity enum.

Lets notices use a green "success" banner in addition to info/warning/
critical. PostgreSQL 12+ allows adding an enum value inside a transaction
as long as the new value is not used in the same transaction (it is not).

Revision ID: 0016_notice_severity_success
Revises: 0015_notices
Create Date: 2026-06-30

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016_notice_severity_success"
down_revision: str | None = "0015_notices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``success`` value to ``notice_severity``."""
    op.execute("ALTER TYPE notice_severity ADD VALUE IF NOT EXISTS 'success'")


def downgrade() -> None:
    """No-op: PostgreSQL cannot drop a value from an enum type."""
