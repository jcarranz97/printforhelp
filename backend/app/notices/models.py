"""SQLAlchemy models for site notices and their per-language copy."""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel

from .constants import NoticeSeverity, NoticeStatus


class Notice(BaseModel):
    """A site notice rendered as a banner.

    A Notice is in exactly one *mode* (enforced by ``notice_one_mode``):

    - **Page mode** — a non-empty ``scopes`` array picks which pages show
      the banner (``all`` shows everywhere); ``target_*`` are NULL.
    - **Entity mode** — ``target_type`` + ``target_id`` attach the notice
      to a single Resource, CollectionCenter, or Request, shown on that
      item's detail page; ``scopes`` is empty.

    Owners may *request* an entity notice (status ``pending``); a
    maintainer/admin approves it before it shows. Localized title/message
    live in :class:`NoticeTranslation` so languages can be added with no
    schema change. A notice is publicly displayed only when it is
    ``approved``, ``enabled`` and ``active`` (and has ≥1 translation).
    """

    __tablename__ = "notices"
    __table_args__ = (
        CheckConstraint(
            "(target_type IS NOT NULL AND target_id IS NOT NULL "
            "AND cardinality(scopes) = 0) OR "
            "(target_type IS NULL AND target_id IS NULL "
            "AND cardinality(scopes) > 0)",
            name="notice_one_mode",
        ),
        CheckConstraint(
            "(status != 'approved') OR (approved_by_id IS NOT NULL)",
            name="notice_approved_implies_approver",
        ),
    )

    severity: Mapped[NoticeSeverity] = mapped_column(
        Enum(
            NoticeSeverity,
            name="notice_severity",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=NoticeSeverity.INFO,
        index=True,
    )
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    target_type: Mapped[str | None] = mapped_column(String(64), index=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[NoticeStatus] = mapped_column(
        Enum(
            NoticeStatus,
            name="notice_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=NoticeStatus.PENDING,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    decline_reason: Mapped[str | None] = mapped_column(Text)
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )


class NoticeTranslation(BaseModel):
    """Per-language title/message (and optional CTA) for a :class:`Notice`."""

    __tablename__ = "notice_translations"
    __table_args__ = (
        UniqueConstraint("notice_id", "language", name="uq_notice_translation_lang"),
        CheckConstraint(
            "(action_url IS NULL) = (action_label IS NULL)",
            name="notice_translation_action_pairing",
        ),
    )

    notice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # BCP-47/ISO code (e.g. "en", "es"). Plain text so new languages need
    # no migration.
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional call-to-action link, localizable per language (e.g. the ES
    # vs EN community group). Both columns are set together (CHECK above).
    action_label: Mapped[str | None] = mapped_column(Text)
    action_url: Mapped[str | None] = mapped_column(Text)
