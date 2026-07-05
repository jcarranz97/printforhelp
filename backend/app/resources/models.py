"""SQLAlchemy model for the Resource catalog."""

import uuid

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import ResourceCategory, ResourceStatus


class Resource(BaseModel):
    """An entry in the shared aid catalog. Polymorphic ownership (FR-016).

    A Resource is most often a 3D-printable design (``category=print_3d``,
    the only kind surfaced in v1), but the model is generic so the same
    catalog can later hold non-printed supplies (food, water, medicine,
    etc.) without a schema migration. ``source_url`` (the STL/model link)
    is required for ``print_3d`` and optional for every other category;
    ``unit`` records the unit of measure (NULL means countable pieces).

    ``creator_id`` is immutable historical attribution; the current owner is
    a User or Organization tracked via the two nullable owner FKs and may
    change over time through an ownership transfer (Phase 5).
    """

    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_organization_id IS NULL) OR "
            "(owner_user_id IS NULL AND owner_organization_id IS NOT NULL)",
            name="resources_one_owner",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ResourceCategory] = mapped_column(
        Enum(
            ResourceCategory,
            name="resource_category",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ResourceCategory.PRINT_3D,
        index=True,
    )
    # Required for print_3d (the STL/model link); optional for other
    # categories (a generic supply may have no canonical source URL).
    source_url: Mapped[str | None] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(500))
    # Focal point (percent, 0-100) of the image kept centered when a fixed
    # aspect box crops it (CSS ``object-position``). Defaults to the center.
    image_focus_x: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="50"
    )
    image_focus_y: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="50"
    )
    # Optional print-on-the-package label image (e.g. a "Donación médica"
    # banner naming the piece). Makers can fold it into the QR bundle PDF/PNG
    # so each printed sticker carries the label above its tracking QR.
    label_image_url: Mapped[str | None] = mapped_column(String(500))
    # Suggested units of measure for the quantity (e.g. "litros", "kg",
    # "cajas"). A supply may accept several; an empty list means countable
    # pieces, which is what every print_3d resource uses. Requesters pick one
    # of these per item (or add their own) when they create a Request item.
    units: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(
            ResourceStatus,
            name="resource_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ResourceStatus.ACTIVE,
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
