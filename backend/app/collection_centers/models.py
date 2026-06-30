"""SQLAlchemy models for collection centers and their contributors."""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import CollectionCenterRole, CollectionCenterStatus


class CollectionCenter(BaseModel):
    """A physical drop-off location. Polymorphic ownership (FR-083)."""

    __tablename__ = "collection_centers"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_organization_id IS NULL) OR "
            "(owner_user_id IS NULL AND owner_organization_id IS NOT NULL)",
            name="cc_one_owner",
        ),
        CheckConstraint(
            "(verified = FALSE) OR (verified_by_id IS NOT NULL)",
            name="cc_verified_implies_verifier",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str | None] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    contact: Mapped[str] = mapped_column(String(255), nullable=False)
    location_url: Mapped[str | None] = mapped_column(Text)
    opening_hours: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    verified: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    registered_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    owner_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    status: Mapped[CollectionCenterStatus] = mapped_column(
        Enum(
            CollectionCenterStatus,
            name="collection_center_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=CollectionCenterStatus.ACTIVE,
        index=True,
    )


class CollectionCenterMembership(BaseModel):
    """A per-center contributor (the owner is on the Center, §6.7)."""

    __tablename__ = "collection_center_memberships"

    collection_center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collection_centers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[CollectionCenterRole] = mapped_column(
        Enum(
            CollectionCenterRole,
            name="collection_center_role",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=CollectionCenterRole.CONTRIBUTOR,
    )
    invited_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
