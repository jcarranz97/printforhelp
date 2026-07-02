"""Resources catalog business logic: CRUD, discontinue, archive (Phase 4)."""

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
from .constants import ResourceCategory, ResourceStatus
from .exceptions import (
    NotEffectiveOwnerExceptionError,
    ResourceArchiveBlockedExceptionError,
    ResourceNotFoundExceptionError,
    SourceUrlRequiredExceptionError,
)


def _assert_source_url_for_category(
    category: ResourceCategory, source_url: str | None
) -> None:
    """A ``print_3d`` Resource must carry a ``source_url`` (the model link)."""
    if category == ResourceCategory.PRINT_3D and not source_url:
        raise SourceUrlRequiredExceptionError


def get_or_raise(db: Session, resource_id: UUID) -> models.Resource:
    """Return a Resource by id or raise ``NotFound``."""
    resource = (
        db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    )
    if resource is None:
        raise ResourceNotFoundExceptionError(resource_id)
    return resource


def is_effective_owner(db: Session, resource: models.Resource, user: User) -> bool:
    """Return True if the user has owner powers on the Resource (or override)."""
    return has_global_override(user) or user.id in effective_owner_user_ids(
        db, resource
    )


def _assert_effective_owner(db: Session, resource: models.Resource, user: User) -> None:
    if not is_effective_owner(db, resource, user):
        raise NotEffectiveOwnerExceptionError


def open_request_item_count(db: Session, resource_id: UUID) -> int:
    """Count active, ``open`` RequestItems referencing the Resource (FR-076)."""
    from app.requests.constants import RequestStatus
    from app.requests.models import RequestItem

    return (
        db.query(RequestItem)
        .filter(
            RequestItem.resource_id == resource_id,
            RequestItem.active.is_(True),
            RequestItem.status == RequestStatus.OPEN,
        )
        .count()
    )


def list_resources(
    db: Session,
    tag: str | None = None,
    status: ResourceStatus | None = None,
    search: str | None = None,
    category: ResourceCategory | None = None,
) -> list[models.Resource]:
    """List active Resources for the public catalog (FR-021).

    ``category`` is accepted for the future generic-supply catalog; v1
    clients omit it and receive every category (all ``print_3d`` today).
    """
    query = db.query(models.Resource).filter(models.Resource.active.is_(True))
    if status is not None:
        query = query.filter(models.Resource.status == status)
    if category is not None:
        query = query.filter(models.Resource.category == category)
    if tag is not None:
        query = query.filter(models.Resource.tags.contains([tag]))
    if search is not None:
        pattern = f"%{search}%"
        query = query.filter(
            models.Resource.name.ilike(pattern)
            | models.Resource.description.ilike(pattern)
        )
    return query.order_by(models.Resource.name.asc()).all()


def create_resource(
    db: Session, payload: schemas.ResourceCreate, actor: User
) -> models.Resource:
    """Register a Resource; owner defaults to the caller (FR-015)."""
    _assert_source_url_for_category(payload.category, payload.source_url)
    owner_user_id, owner_organization_id = assert_caller_can_own_on_behalf_of(
        db, actor, payload.owner_organization_id
    )
    resource = models.Resource(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        source_url=payload.source_url,
        image_url=payload.image_url,
        label_image_url=payload.label_image_url,
        units=payload.units,
        tags=payload.tags,
        creator_id=actor.id,
        owner_user_id=owner_user_id,
        owner_organization_id=owner_organization_id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def update_resource(
    db: Session, resource_id: UUID, payload: schemas.ResourceUpdate, actor: User
) -> models.Resource:
    """Edit a Resource's mutable fields (effective owner)."""
    resource = get_or_raise(db, resource_id)
    _assert_effective_owner(db, resource, actor)
    fields = payload.model_dump(exclude_unset=True)
    # Validate the resulting state: a print_3d resource must keep a
    # source_url, whether the category or the URL is the field changing.
    final_category = fields.get("category", resource.category)
    final_source_url = fields.get("source_url", resource.source_url)
    _assert_source_url_for_category(final_category, final_source_url)
    for field, value in fields.items():
        setattr(resource, field, value)
    db.commit()
    db.refresh(resource)
    return resource


def set_status(
    db: Session, resource_id: UUID, status: ResourceStatus, actor: User
) -> models.Resource:
    """Discontinue or reactivate a Resource (effective owner, FR-075)."""
    resource = get_or_raise(db, resource_id)
    _assert_effective_owner(db, resource, actor)
    resource.status = status
    db.commit()
    db.refresh(resource)
    return resource


def archive_resource(db: Session, resource_id: UUID, actor: User) -> models.Resource:
    """Owner-side archive; blocked while open Requests reference it (FR-076)."""
    resource = get_or_raise(db, resource_id)
    _assert_effective_owner(db, resource, actor)
    open_count = open_request_item_count(db, resource_id)
    if open_count > 0:
        raise ResourceArchiveBlockedExceptionError(open_count)
    resource.active = False
    resource.status = ResourceStatus.DISCONTINUED
    db.commit()
    db.refresh(resource)
    return resource


def force_archive_resource(
    db: Session, resource_id: UUID, actor: User
) -> models.Resource:
    """Maintainer/admin force-archive; cascades open items closed (FR-077)."""
    from app.requests.service import close_open_items_for_resource

    resource = get_or_raise(db, resource_id)
    close_open_items_for_resource(db, resource_id, actor)
    resource.active = False
    resource.status = ResourceStatus.DISCONTINUED
    write_audit(
        db,
        actor.id,
        AuditAction.FORCE_ARCHIVE_RESOURCE,
        AuditTargetType.RESOURCE,
        resource.id,
    )
    db.commit()
    db.refresh(resource)
    return resource
