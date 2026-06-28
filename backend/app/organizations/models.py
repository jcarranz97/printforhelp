"""SQLAlchemy models for organizations and their memberships."""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import OrganizationRole, OrganizationStatus


class Organization(BaseModel):
    """A named group that can own assets on behalf of its members (§3.9)."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "(verified = FALSE) OR (verified_by_id IS NOT NULL)",
            name="verified_implies_verifier",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    contact: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    country: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    verified: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    registered_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(
            OrganizationStatus,
            name="organization_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
        index=True,
    )


class OrganizationMembership(BaseModel):
    """Links a user to an organization as ``owner`` or ``member`` (§6.9)."""

    __tablename__ = "organization_memberships"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrganizationRole] = mapped_column(
        Enum(
            OrganizationRole,
            name="organization_role",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
