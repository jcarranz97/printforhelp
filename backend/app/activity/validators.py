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
from app.requests.models import Request, RequestItem
from app.resources.models import Resource
from app.shipments.models import Shipment
from app.tracking.models import TrackingGroup

from .constants import EntityType

_ENTITY_MODELS: dict[EntityType, type[BaseModel]] = {
    EntityType.COLLECTION_CENTER: CollectionCenter,
    EntityType.SHIPMENT: Shipment,
    EntityType.RESOURCE: Resource,
    EntityType.REQUEST: Request,
    EntityType.REQUEST_ITEM: RequestItem,
    EntityType.TRACKING_GROUP: TrackingGroup,
}


def entity_exists(db: Session, entity_type: EntityType, entity_id: UUID) -> bool:
    """Return True if an active entity of the given type/id exists."""
    model = _ENTITY_MODELS[entity_type]
    return (
        db.query(model.id).filter(model.id == entity_id, model.active.is_(True)).first()
        is not None
    )
