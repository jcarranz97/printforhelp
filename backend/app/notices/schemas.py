"""Pydantic request/response models for the notices domain."""

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .constants import NoticeSeverity, NoticeStatus, NoticeTargetType, PageScope


def _validate_http_url(value: str | None) -> str | None:
    """Normalize an optional absolute ``http(s)`` URL (empty -> ``None``)."""
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if not trimmed.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return trimmed


class NoticeTranslationIn(BaseModel):
    """A single-language title/message (and optional CTA) on input."""

    language: str = Field(min_length=2, max_length=8)
    title: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=1)
    action_label: str | None = Field(default=None, max_length=120)
    action_url: str | None = Field(default=None, max_length=2000)

    _normalize_action_url = field_validator("action_url")(_validate_http_url)

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, value: str) -> str:
        """Lowercase the language code so lookups are case-insensitive."""
        return value.strip().lower()

    @field_validator("title", "action_label")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        """Collapse blank optional text fields to ``None``."""
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @model_validator(mode="after")
    def _check_action_pairing(self) -> "NoticeTranslationIn":
        """A CTA needs both a label and a URL, or neither."""
        if (self.action_url is None) != (self.action_label is None):
            raise ValueError("action_url and action_label must be set together")
        return self


class NoticeTranslationOut(BaseModel):
    """Public representation of a notice translation."""

    model_config = ConfigDict(from_attributes=True)

    language: str
    title: str | None
    message: str
    action_label: str | None
    action_url: str | None


class NoticeCreate(BaseModel):
    """Create a notice directly (maintainer/admin).

    Provide ``scopes`` for a page banner OR ``target_type`` + ``target_id``
    for an entity notice. Exactly-one-mode, non-empty translations and
    unique languages are enforced in the service layer.
    """

    severity: NoticeSeverity = NoticeSeverity.INFO
    scopes: list[PageScope] = Field(default_factory=list)
    target_type: NoticeTargetType | None = None
    target_id: UUID | None = None
    translations: list[NoticeTranslationIn] = Field(default_factory=list)


class NoticeRequest(BaseModel):
    """Request an entity notice (owner) — always entity mode."""

    severity: NoticeSeverity = NoticeSeverity.INFO
    target_type: NoticeTargetType
    target_id: UUID
    translations: list[NoticeTranslationIn] = Field(default_factory=list)


class NoticeUpdate(BaseModel):
    """Edit a notice's severity, scopes, and/or translations (maintainer)."""

    severity: NoticeSeverity | None = None
    scopes: list[PageScope] | None = None
    translations: list[NoticeTranslationIn] | None = None


class NoticeDecline(BaseModel):
    """Optional reason when declining a pending notice."""

    reason: str | None = None


class NoticeResponse(BaseModel):
    """Full representation of a notice, including its translations."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    severity: NoticeSeverity
    scopes: list[str]
    target_type: str | None
    target_id: UUID | None
    status: NoticeStatus
    enabled: bool
    decline_reason: str | None
    requested_by_id: UUID
    approved_by_id: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime
    translations: list[NoticeTranslationOut]
