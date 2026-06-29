"""Generalize the Parts catalog into a generic ``resources`` catalog.

Forward-compat for non-3D aid (food, water, medicine, ...). Renames the
``parts`` table/enum/constraints to ``resources`` and adds the pieces a
generic supply catalog needs:

* a ``resource_category`` enum (``print_3d`` is the only value used in v1),
* a nullable ``unit`` (unit of measure; NULL means countable pieces),
* relaxes ``source_url`` to NULLable (required for ``print_3d`` is enforced
  in the service layer, not the schema).

The ``request_items.part_id`` FK column is renamed to ``resource_id``.

Revision ID: 0010_resources_generic
Revises: 0009_request_image
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_resources_generic"
down_revision: str | None = "0009_request_image"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORY_VALUES = (
    "print_3d",
    "food",
    "water",
    "medicine",
    "hygiene",
    "clothing",
    "tools",
    "other",
)

_PARTS_INDEXES = (
    ("ix_parts_status", "ix_resources_status"),
    ("ix_parts_featured", "ix_resources_featured"),
    ("ix_parts_owner_user", "ix_resources_owner_user"),
    ("ix_parts_owner_org", "ix_resources_owner_org"),
)


def upgrade() -> None:
    """Rename parts -> resources and add the generic-catalog columns."""
    # 1. Rename the status enum type (the status column follows it).
    op.execute("ALTER TYPE part_status RENAME TO resource_status")

    # 2. Rename the table, its named CHECK constraint, and its indexes.
    op.rename_table("parts", "resources")
    op.execute(
        "ALTER TABLE resources RENAME CONSTRAINT parts_one_owner "
        "TO resources_one_owner"
    )
    for old, new in _PARTS_INDEXES:
        op.execute(f"ALTER INDEX {old} RENAME TO {new}")

    # 3. New ``resource_category`` enum + the ``category`` column.
    resource_category = postgresql.ENUM(*_CATEGORY_VALUES, name="resource_category")
    resource_category.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "resources",
        sa.Column(
            "category",
            postgresql.ENUM(name="resource_category", create_type=False),
            nullable=False,
            server_default="print_3d",
        ),
    )
    op.create_index("ix_resources_category", "resources", ["category"])

    # 4. Unit of measure, and relax source_url (optional for non-3D items).
    op.add_column("resources", sa.Column("unit", sa.String(32), nullable=True))
    op.alter_column("resources", "source_url", existing_type=sa.String(500), nullable=True)

    # 5. Rename the request_items FK column + its index.
    op.alter_column("request_items", "part_id", new_column_name="resource_id")
    op.execute(
        "ALTER INDEX ix_request_items_part RENAME TO ix_request_items_resource"
    )


def downgrade() -> None:
    """Reverse the rename and drop the generic-catalog columns."""
    op.execute(
        "ALTER INDEX ix_request_items_resource RENAME TO ix_request_items_part"
    )
    op.alter_column("request_items", "resource_id", new_column_name="part_id")

    op.alter_column(
        "resources", "source_url", existing_type=sa.String(500), nullable=False
    )
    op.drop_column("resources", "unit")
    op.drop_index("ix_resources_category", table_name="resources")
    op.drop_column("resources", "category")
    postgresql.ENUM(name="resource_category").drop(op.get_bind(), checkfirst=True)

    for old, new in _PARTS_INDEXES:
        op.execute(f"ALTER INDEX {new} RENAME TO {old}")
    op.execute(
        "ALTER TABLE resources RENAME CONSTRAINT resources_one_owner "
        "TO parts_one_owner"
    )
    op.rename_table("resources", "parts")
    op.execute("ALTER TYPE resource_status RENAME TO part_status")
