"""Parts catalog business logic: CRUD, discontinue, archive (Phase 4)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.permissions import (
    assert_caller_can_own_on_behalf_of,
    effective_owner_user_ids,
    has_global_override,
)
from app.users.models import User

from . import models, schemas
from .constants import PartStatus
from .exceptions import (
    NotEffectiveOwnerExceptionError,
    PartArchiveBlockedExceptionError,
    PartNotFoundExceptionError,
)


def get_or_raise(db: Session, part_id: UUID) -> models.Part:
    """Return a Part by id or raise ``NotFound``."""
    part = db.query(models.Part).filter(models.Part.id == part_id).first()
    if part is None:
        raise PartNotFoundExceptionError(part_id)
    return part


def is_effective_owner(db: Session, part: models.Part, user: User) -> bool:
    """Return True if the user has owner powers on the Part (or override)."""
    return has_global_override(user) or user.id in effective_owner_user_ids(db, part)


def _assert_effective_owner(db: Session, part: models.Part, user: User) -> None:
    if not is_effective_owner(db, part, user):
        raise NotEffectiveOwnerExceptionError


def open_request_item_count(db: Session, part_id: UUID) -> int:
    """Count active, ``open`` RequestItems referencing the Part (FR-076)."""
    from app.requests.constants import RequestStatus
    from app.requests.models import RequestItem

    return (
        db.query(RequestItem)
        .filter(
            RequestItem.part_id == part_id,
            RequestItem.active.is_(True),
            RequestItem.status == RequestStatus.OPEN,
        )
        .count()
    )


def list_parts(
    db: Session,
    tag: str | None = None,
    status: PartStatus | None = None,
    search: str | None = None,
) -> list[models.Part]:
    """List active Parts for the public catalog (FR-021)."""
    query = db.query(models.Part).filter(models.Part.active.is_(True))
    if status is not None:
        query = query.filter(models.Part.status == status)
    if tag is not None:
        query = query.filter(models.Part.tags.contains([tag]))
    if search is not None:
        pattern = f"%{search}%"
        query = query.filter(
            models.Part.name.ilike(pattern) | models.Part.description.ilike(pattern)
        )
    return query.order_by(models.Part.name.asc()).all()


def create_part(db: Session, payload: schemas.PartCreate, actor: User) -> models.Part:
    """Register a Part; owner defaults to the caller (FR-015)."""
    owner_user_id, owner_organization_id = assert_caller_can_own_on_behalf_of(
        db, actor, payload.owner_organization_id
    )
    part = models.Part(
        name=payload.name,
        description=payload.description,
        source_url=payload.source_url,
        image_url=payload.image_url,
        tags=payload.tags,
        creator_id=actor.id,
        owner_user_id=owner_user_id,
        owner_organization_id=owner_organization_id,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


def update_part(
    db: Session, part_id: UUID, payload: schemas.PartUpdate, actor: User
) -> models.Part:
    """Edit a Part's mutable fields (effective owner)."""
    part = get_or_raise(db, part_id)
    _assert_effective_owner(db, part, actor)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(part, field, value)
    db.commit()
    db.refresh(part)
    return part


def set_status(
    db: Session, part_id: UUID, status: PartStatus, actor: User
) -> models.Part:
    """Discontinue or reactivate a Part (effective owner, FR-075)."""
    part = get_or_raise(db, part_id)
    _assert_effective_owner(db, part, actor)
    part.status = status
    db.commit()
    db.refresh(part)
    return part


def archive_part(db: Session, part_id: UUID, actor: User) -> models.Part:
    """Owner-side archive; blocked while open Requests reference it (FR-076)."""
    part = get_or_raise(db, part_id)
    _assert_effective_owner(db, part, actor)
    open_count = open_request_item_count(db, part_id)
    if open_count > 0:
        raise PartArchiveBlockedExceptionError(open_count)
    part.active = False
    part.status = PartStatus.DISCONTINUED
    db.commit()
    db.refresh(part)
    return part


def force_archive_part(db: Session, part_id: UUID, actor: User) -> models.Part:
    """Maintainer/admin force-archive; cascades open items closed (FR-077)."""
    from app.requests.service import close_open_items_for_part

    part = get_or_raise(db, part_id)
    close_open_items_for_part(db, part_id, actor)
    part.active = False
    part.status = PartStatus.DISCONTINUED
    write_audit(
        db,
        actor.id,
        AuditAction.FORCE_ARCHIVE_PART,
        AuditTargetType.PART,
        part.id,
    )
    db.commit()
    db.refresh(part)
    return part
