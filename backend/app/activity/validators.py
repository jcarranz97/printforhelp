"""Existence checks for polymorphic comment targets.

Kept separate from ``service.py`` so the service never imports another
domain's models at call time. The registry maps each commentable
``EntityType`` to the ORM model that backs it; commenting on an entity
requires an active row to exist (FR-131).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.collection_centers.models import CollectionCenter
from app.models import BaseModel
from app.shipments.models import Shipment

from .constants import EntityType

_ENTITY_MODELS: dict[EntityType, type[BaseModel]] = {
    EntityType.COLLECTION_CENTER: CollectionCenter,
    EntityType.SHIPMENT: Shipment,
}


def entity_exists(db: Session, entity_type: EntityType, entity_id: UUID) -> bool:
    """Return True if an active entity of the given type/id exists."""
    model = _ENTITY_MODELS[entity_type]
    return (
        db.query(model.id).filter(model.id == entity_id, model.active.is_(True)).first()
        is not None
    )
