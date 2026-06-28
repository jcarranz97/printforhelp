"""SQLAlchemy model for the Part catalog."""

import uuid

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import PartStatus


class Part(BaseModel):
    """A printable design in the shared catalog. Polymorphic ownership (FR-016).

    ``creator_id`` is immutable historical attribution; the current owner is
    a User or Organization tracked via the two nullable owner FKs and may
    change over time through an ownership transfer (Phase 5).
    """

    __tablename__ = "parts"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_organization_id IS NULL) OR "
            "(owner_user_id IS NULL AND owner_organization_id IS NOT NULL)",
            name="parts_one_owner",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    status: Mapped[PartStatus] = mapped_column(
        Enum(
            PartStatus,
            name="part_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=PartStatus.ACTIVE,
        index=True,
    )
    featured: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    owner_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
