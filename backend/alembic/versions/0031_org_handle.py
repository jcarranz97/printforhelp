"""Add a URL-safe public ``handle`` to organizations.

Organizations get a profile URL (``/{handle}``) that shares one namespace
with user usernames, so the handle must be URL-safe and unique across both.
This migration adds the column, backfills a slug from each org's name
(deduped against existing usernames, already-assigned handles, and a small
reserved-word set), then makes it NOT NULL with a unique index.

Revision ID: 0031_org_handle
Revises: 0030_resource_image_focus
Create Date: 2026-07-05
"""

import re
import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031_org_handle"
down_revision: str | None = "0030_resource_image_focus"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Minimal reserved set for the backfill so no legacy org handle shadows a
# core route (kept small and self-contained; the app owns the full list).
_RESERVED = {
    "admin",
    "api",
    "auth",
    "login",
    "logout",
    "register",
    "me",
    "about",
    "centers",
    "parts",
    "requests",
    "supplies",
    "track",
    "orgs",
    "organizations",
}


def _slugify(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not slug:
        slug = "org"
    if len(slug) < 3:
        slug = f"{slug}-org"
    return slug[:50].strip("-")


def _backfill(conn: sa.Connection) -> None:
    taken: set[str] = set(_RESERVED)
    for (username,) in conn.execute(sa.text("SELECT username FROM users")):
        taken.add(username.lower())

    rows = conn.execute(
        sa.text("SELECT id, name FROM organizations ORDER BY created_at")
    ).all()
    for org_id, name in rows:
        base = _slugify(name)
        candidate = base
        suffix = 1
        while candidate in taken:
            suffix += 1
            candidate = f"{base}-{suffix}"[:50].strip("-")
        taken.add(candidate)
        conn.execute(
            sa.text("UPDATE organizations SET handle = :h WHERE id = :i"),
            {"h": candidate, "i": org_id},
        )


def upgrade() -> None:
    """Add ``handle``, backfill it, then enforce NOT NULL + uniqueness."""
    op.add_column(
        "organizations", sa.Column("handle", sa.String(length=50), nullable=True)
    )
    _backfill(op.get_bind())
    op.alter_column("organizations", "handle", nullable=False)
    op.create_index(
        "ix_organizations_handle", "organizations", ["handle"], unique=True
    )


def downgrade() -> None:
    """Drop the ``handle`` column and its unique index."""
    op.drop_index("ix_organizations_handle", table_name="organizations")
    op.drop_column("organizations", "handle")
