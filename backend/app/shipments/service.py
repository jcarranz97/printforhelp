"""Shipment business logic: public reads, member-gated writes (FR-127..130).

Shipments belong to a Collection Center. Reads are public so the
community can see drop-off deadlines; writes require an effective member
of the center (owner, contributor, owning-org member) or a maintainer /
admin. Every mutation is mirrored into the public activity timeline.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.activity import service as activity_service
from app.activity.constants import ActivityAction, EntityType
from app.collection_centers import service as cc_service
from app.collection_centers.exceptions import NotEffectiveMemberExceptionError
from app.users.models import User

from . import models, schemas
from .constants import ShipmentStatus
from .exceptions import ShipmentNotFoundExceptionError


def _assert_can_manage(db: Session, collection_center_id: UUID, actor: User) -> None:
    """Require the actor to be an effective member of the center (FR-129)."""
    cc = cc_service.get_or_raise(db, collection_center_id)
    if not cc_service.is_effective_member(db, cc, actor):
        raise NotEffectiveMemberExceptionError


def get_or_raise(
    db: Session, collection_center_id: UUID, shipment_id: UUID
) -> models.Shipment:
    """Return an active shipment scoped to its center, or raise ``NotFound``."""
    shipment = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.id == shipment_id,
            models.Shipment.collection_center_id == collection_center_id,
            models.Shipment.active.is_(True),
        )
        .first()
    )
    if shipment is None:
        raise ShipmentNotFoundExceptionError(shipment_id)
    return shipment


def list_shipments(db: Session, collection_center_id: UUID) -> list[models.Shipment]:
    """List a center's active shipments, soonest date first (public, FR-130)."""
    cc_service.get_or_raise(db, collection_center_id)
    return (
        db.query(models.Shipment)
        .filter(
            models.Shipment.collection_center_id == collection_center_id,
            models.Shipment.active.is_(True),
        )
        .order_by(models.Shipment.shipment_date.asc())
        .all()
    )


def create_shipment(
    db: Session,
    collection_center_id: UUID,
    payload: schemas.ShipmentCreate,
    actor: User,
) -> models.Shipment:
    """Create a shipment (effective member or maintainer/admin, FR-129)."""
    _assert_can_manage(db, collection_center_id, actor)
    shipment = models.Shipment(
        collection_center_id=collection_center_id,
        shipment_date=payload.shipment_date,
        status=payload.status,
        destination=payload.destination,
        description=payload.description,
        created_by_id=actor.id,
    )
    db.add(shipment)
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor.id,
        action=ActivityAction.CREATED,
        changes={
            "shipment_date": payload.shipment_date.isoformat(),
            "status": payload.status.value,
        },
    )
    db.commit()
    db.refresh(shipment)
    return shipment


def update_shipment(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    payload: schemas.ShipmentUpdate,
    actor: User,
) -> models.Shipment:
    """Edit a shipment, recording status transitions distinctly (FR-129)."""
    _assert_can_manage(db, collection_center_id, actor)
    shipment = get_or_raise(db, collection_center_id, shipment_id)

    fields = payload.model_dump(exclude_unset=True)
    old_status = shipment.status
    new_status: ShipmentStatus | None = fields.get("status")
    for field, value in fields.items():
        setattr(shipment, field, value)
    db.flush()

    if new_status is not None and new_status != old_status:
        activity_service.record(
            db,
            entity_type=EntityType.SHIPMENT,
            entity_id=shipment.id,
            actor_user_id=actor.id,
            action=ActivityAction.STATUS_CHANGED,
            changes={"status": {"from": old_status.value, "to": new_status.value}},
        )
    else:
        activity_service.record(
            db,
            entity_type=EntityType.SHIPMENT,
            entity_id=shipment.id,
            actor_user_id=actor.id,
            action=ActivityAction.UPDATED,
            changes={k: str(v) for k, v in fields.items()},
        )

    db.commit()
    db.refresh(shipment)
    return shipment


def delete_shipment(
    db: Session,
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: User,
) -> None:
    """Soft-delete a shipment (effective member or maintainer/admin)."""
    _assert_can_manage(db, collection_center_id, actor)
    shipment = get_or_raise(db, collection_center_id, shipment_id)
    shipment.active = False
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=actor.id,
        action=ActivityAction.DELETED,
        changes={},
    )
    db.commit()
