"""Notices business logic: create/request, approve/decline, listing.

Cross-domain loaders (Resource / CollectionCenter / Request) are imported
function-locally to keep the import graph acyclic, the same convention the
other orchestrating service layers use.
"""

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.permissions import (
    effective_owner_user_ids,
    effective_requester_user_ids,
    has_global_override,
)
from app.users.models import User

from . import models, schemas
from .constants import NoticeStatus, NoticeTargetType, PageScope
from .exceptions import (
    DuplicateLanguageExceptionError,
    InvalidNoticeModeExceptionError,
    NotEntityOwnerExceptionError,
    NoticeNotFoundExceptionError,
    NoticeNotPendingExceptionError,
    TranslationsRequiredExceptionError,
)


def get_or_raise(db: Session, notice_id: UUID) -> models.Notice:
    """Return a Notice by id or raise ``NotFound``."""
    notice = db.query(models.Notice).filter(models.Notice.id == notice_id).first()
    if notice is None:
        raise NoticeNotFoundExceptionError(notice_id)
    return notice


def _validate_translations(translations: Sequence[schemas.NoticeTranslationIn]) -> None:
    """A notice needs ≥1 translation with no duplicate language codes."""
    if not translations:
        raise TranslationsRequiredExceptionError
    seen: set[str] = set()
    for translation in translations:
        if translation.language in seen:
            raise DuplicateLanguageExceptionError(translation.language)
        seen.add(translation.language)


def _validate_page_mode(scopes: Sequence[PageScope]) -> None:
    """A page-mode notice needs at least one scope and no entity target."""
    if not scopes:
        raise InvalidNoticeModeExceptionError


def _resolve_mode(
    scopes: Sequence[PageScope],
    target_type: NoticeTargetType | None,
    target_id: UUID | None,
) -> None:
    """Enforce exactly one of page mode / entity mode."""
    has_scopes = bool(scopes)
    has_target = target_type is not None or target_id is not None
    if has_scopes == has_target:
        raise InvalidNoticeModeExceptionError
    if has_target and (target_type is None or target_id is None):
        raise InvalidNoticeModeExceptionError


def _load_target(db: Session, target_type: NoticeTargetType, target_id: UUID) -> object:
    """Load the targeted entity by type or raise its domain ``NotFound``."""
    if target_type == NoticeTargetType.RESOURCE:
        from app.resources import service as resources_service

        return resources_service.get_or_raise(db, target_id)
    if target_type == NoticeTargetType.COLLECTION_CENTER:
        from app.collection_centers import service as cc_service

        return cc_service.get_or_raise(db, target_id)
    from app.requests import service as requests_service

    return requests_service.get_request_or_raise(db, target_id)


def assert_can_request_on_target(
    db: Session, user: User, target_type: NoticeTargetType, target_id: UUID
) -> object:
    """Ensure ``user`` effectively owns the target (or has a global override)."""
    from app.requests.models import Request

    target = _load_target(db, target_type, target_id)
    if has_global_override(user):
        return target
    if isinstance(target, Request):
        owner_ids = effective_requester_user_ids(db, target)
    else:
        owner_ids = effective_owner_user_ids(db, target)  # type: ignore[arg-type]
    if user.id not in owner_ids:
        raise NotEntityOwnerExceptionError
    return target


def _persist_translations(
    db: Session,
    notice_id: UUID,
    translations: Sequence[schemas.NoticeTranslationIn],
) -> None:
    """Insert translation rows for a notice."""
    for translation in translations:
        db.add(
            models.NoticeTranslation(
                notice_id=notice_id,
                language=translation.language,
                title=translation.title,
                message=translation.message,
                action_label=translation.action_label,
                action_url=translation.action_url,
            )
        )


def create_notice(
    db: Session, payload: schemas.NoticeCreate, actor: User
) -> models.Notice:
    """Create an approved notice directly (maintainer/admin)."""
    _validate_translations(payload.translations)
    _resolve_mode(payload.scopes, payload.target_type, payload.target_id)
    if payload.target_type is not None and payload.target_id is not None:
        _load_target(db, payload.target_type, payload.target_id)
    notice = models.Notice(
        severity=payload.severity,
        scopes=[scope.value for scope in payload.scopes],
        target_type=payload.target_type.value if payload.target_type else None,
        target_id=payload.target_id,
        status=NoticeStatus.APPROVED,
        enabled=True,
        requested_by_id=actor.id,
        approved_by_id=actor.id,
    )
    db.add(notice)
    db.flush()
    _persist_translations(db, notice.id, payload.translations)
    write_audit(
        db, actor.id, AuditAction.CREATE_NOTICE, AuditTargetType.NOTICE, notice.id
    )
    db.commit()
    db.refresh(notice)
    return notice


def request_notice(
    db: Session, payload: schemas.NoticeRequest, actor: User
) -> models.Notice:
    """Request an entity notice; owners get ``pending``, maintainers approved."""
    _validate_translations(payload.translations)
    assert_can_request_on_target(db, actor, payload.target_type, payload.target_id)
    approved = has_global_override(actor)
    notice = models.Notice(
        severity=payload.severity,
        scopes=[],
        target_type=payload.target_type.value,
        target_id=payload.target_id,
        status=NoticeStatus.APPROVED if approved else NoticeStatus.PENDING,
        enabled=True,
        requested_by_id=actor.id,
        approved_by_id=actor.id if approved else None,
    )
    db.add(notice)
    db.flush()
    _persist_translations(db, notice.id, payload.translations)
    write_audit(
        db, actor.id, AuditAction.REQUEST_NOTICE, AuditTargetType.NOTICE, notice.id
    )
    db.commit()
    db.refresh(notice)
    return notice


def approve(db: Session, notice_id: UUID, actor: User) -> models.Notice:
    """Approve a pending notice (maintainer/admin)."""
    notice = get_or_raise(db, notice_id)
    if notice.status != NoticeStatus.PENDING:
        raise NoticeNotPendingExceptionError
    notice.status = NoticeStatus.APPROVED
    notice.approved_by_id = actor.id
    notice.decline_reason = None
    write_audit(
        db, actor.id, AuditAction.APPROVE_NOTICE, AuditTargetType.NOTICE, notice.id
    )
    db.commit()
    db.refresh(notice)
    return notice


def decline(
    db: Session, notice_id: UUID, reason: str | None, actor: User
) -> models.Notice:
    """Decline a pending notice (maintainer/admin)."""
    notice = get_or_raise(db, notice_id)
    if notice.status != NoticeStatus.PENDING:
        raise NoticeNotPendingExceptionError
    notice.status = NoticeStatus.DECLINED
    notice.approved_by_id = actor.id
    notice.decline_reason = reason
    write_audit(
        db,
        actor.id,
        AuditAction.DECLINE_NOTICE,
        AuditTargetType.NOTICE,
        notice.id,
        reason=reason,
    )
    db.commit()
    db.refresh(notice)
    return notice


def toggle_enabled(db: Session, notice_id: UUID, actor: User) -> models.Notice:
    """Flip a notice's ``enabled`` flag (maintainer/admin)."""
    notice = get_or_raise(db, notice_id)
    notice.enabled = not notice.enabled
    write_audit(
        db, actor.id, AuditAction.TOGGLE_NOTICE, AuditTargetType.NOTICE, notice.id
    )
    db.commit()
    db.refresh(notice)
    return notice


def update_notice(
    db: Session, notice_id: UUID, payload: schemas.NoticeUpdate
) -> models.Notice:
    """Edit severity, scopes and/or translations (maintainer/admin)."""
    notice = get_or_raise(db, notice_id)
    fields = payload.model_dump(exclude_unset=True)
    if "severity" in fields and payload.severity is not None:
        notice.severity = payload.severity
    if "scopes" in fields and payload.scopes is not None:
        _validate_page_mode(payload.scopes)
        if notice.target_type is not None:
            raise InvalidNoticeModeExceptionError
        notice.scopes = [scope.value for scope in payload.scopes]
    if payload.translations is not None:
        _validate_translations(payload.translations)
        db.query(models.NoticeTranslation).filter(
            models.NoticeTranslation.notice_id == notice.id
        ).delete()
        _persist_translations(db, notice.id, payload.translations)
    db.commit()
    db.refresh(notice)
    return notice


def soft_delete(db: Session, notice_id: UUID, actor: User) -> models.Notice:
    """Archive a notice. Requesters may cancel their own pending one."""
    notice = get_or_raise(db, notice_id)
    if not has_global_override(actor) and not (
        notice.status == NoticeStatus.PENDING and notice.requested_by_id == actor.id
    ):
        raise NotEntityOwnerExceptionError
    notice.active = False
    write_audit(
        db, actor.id, AuditAction.DELETE_NOTICE, AuditTargetType.NOTICE, notice.id
    )
    db.commit()
    db.refresh(notice)
    return notice


def list_public(
    db: Session,
    scope: PageScope | None = None,
    target_type: NoticeTargetType | None = None,
    target_id: UUID | None = None,
) -> list[models.Notice]:
    """List approved, enabled, active notices for the public banners."""
    query = db.query(models.Notice).filter(
        models.Notice.active.is_(True),
        models.Notice.enabled.is_(True),
        models.Notice.status == NoticeStatus.APPROVED,
    )
    if target_type is not None and target_id is not None:
        query = query.filter(
            models.Notice.target_type == target_type.value,
            models.Notice.target_id == target_id,
        )
    elif scope is not None:
        query = query.filter(
            models.Notice.scopes.overlap([scope.value, PageScope.ALL.value])
        )
    else:
        query = query.filter(models.Notice.target_type.is_(None))
    return query.order_by(models.Notice.created_at.desc()).all()


def list_manage(db: Session, status: NoticeStatus | None = None) -> list[models.Notice]:
    """List every active notice for the moderation tab (incl. disabled)."""
    query = db.query(models.Notice).filter(models.Notice.active.is_(True))
    if status is not None:
        query = query.filter(models.Notice.status == status)
    return query.order_by(models.Notice.created_at.desc()).all()


def _translations_by_notice(
    db: Session, notice_ids: Sequence[UUID]
) -> dict[UUID, list[models.NoticeTranslation]]:
    """Group translation rows by notice id in a single query."""
    grouped: dict[UUID, list[models.NoticeTranslation]] = defaultdict(list)
    if not notice_ids:
        return grouped
    rows = (
        db.query(models.NoticeTranslation)
        .filter(models.NoticeTranslation.notice_id.in_(notice_ids))
        .order_by(models.NoticeTranslation.language.asc())
        .all()
    )
    for row in rows:
        grouped[row.notice_id].append(row)
    return grouped


def _serialize(
    notice: models.Notice, translations: Sequence[models.NoticeTranslation]
) -> schemas.NoticeResponse:
    return schemas.NoticeResponse(
        id=notice.id,
        severity=notice.severity,
        scopes=list(notice.scopes),
        target_type=notice.target_type,
        target_id=notice.target_id,
        status=notice.status,
        enabled=notice.enabled,
        decline_reason=notice.decline_reason,
        requested_by_id=notice.requested_by_id,
        approved_by_id=notice.approved_by_id,
        active=notice.active,
        created_at=notice.created_at,
        updated_at=notice.updated_at,
        translations=[
            schemas.NoticeTranslationOut.model_validate(t) for t in translations
        ],
    )


def serialize_one(db: Session, notice: models.Notice) -> schemas.NoticeResponse:
    """Build a response for a single notice (loads its translations)."""
    grouped = _translations_by_notice(db, [notice.id])
    return _serialize(notice, grouped.get(notice.id, []))


def serialize_many(
    db: Session, notices: Sequence[models.Notice]
) -> list[schemas.NoticeResponse]:
    """Build responses for many notices, loading translations in one query."""
    grouped = _translations_by_notice(db, [notice.id for notice in notices])
    return [_serialize(notice, grouped.get(notice.id, [])) for notice in notices]
