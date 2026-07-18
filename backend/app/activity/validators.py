"""Existence checks for polymorphic comment targets.

Kept separate from ``service.py`` so the service never imports another
domain's models at call time. The registry maps each commentable
``EntityType`` to the ORM model that backs it; commenting on an entity
requires an active row to exist (FR-131).
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.collection_centers.models import CollectionCenter
from app.models import BaseModel
from app.requests.models import Request, RequestItem
from app.requests.service import can_view_request, is_effective_requester
from app.resources.models import Resource
from app.shipments.models import Shipment
from app.tracking.models import TrackingGroup

from .constants import EntityType
from .models import Comment

if TYPE_CHECKING:
    from app.users.models import User

_ENTITY_MODELS: dict[EntityType, type[BaseModel]] = {
    EntityType.COLLECTION_CENTER: CollectionCenter,
    EntityType.SHIPMENT: Shipment,
    EntityType.RESOURCE: Resource,
    EntityType.REQUEST: Request,
    # The review thread hangs off the Request row (same id, separate timeline).
    EntityType.REQUEST_REVIEW: Request,
    EntityType.REQUEST_ITEM: RequestItem,
    EntityType.TRACKING_GROUP: TrackingGroup,
    # A comment is reactable; its row backs the existence check directly.
    EntityType.COMMENT: Comment,
}


def entity_exists(db: Session, entity_type: EntityType, entity_id: UUID) -> bool:
    """Return True if an active entity of the given type/id exists."""
    model = _ENTITY_MODELS[entity_type]
    return (
        db.query(model.id).filter(model.id == entity_id, model.active.is_(True)).first()
        is not None
    )


def is_entity_visible(  # noqa: PLR0911 - one branch per polymorphic entity type
    db: Session,
    entity_type: EntityType,
    entity_id: UUID,
    viewer: "User | None",
) -> bool:
    """Whether ``viewer`` may read this entity's comments/activity.

    Only Requests carry a moderation gate today (FR-134): an unpublished
    campaign — and each of its items — is readable solely by its requesters and
    by maintainers/admins. Because a pre-publication link leaks the entity UUID,
    hiding the campaign page alone is not enough; its comment and activity
    feeds have to honour the same rule or the content is still reachable.

    Unknown ids return True so missing entities keep their existing
    empty/404 behaviour rather than being masked as "forbidden".
    """
    if entity_type is EntityType.REQUEST_REVIEW:
        # The moderation thread. Unlike everything else here, this is private
        # **permanently** — approving the campaign publishes the campaign, not
        # the conversation that vetted it. Only the requesters and
        # maintainers/admins ever read or write it.
        request = db.query(Request).filter(Request.id == entity_id).first()
        if request is None:
            return True
        return viewer is not None and is_effective_requester(db, request, viewer)
    if entity_type is EntityType.REQUEST:
        request = db.query(Request).filter(Request.id == entity_id).first()
        return request is None or can_view_request(db, request, viewer)
    if entity_type is EntityType.REQUEST_ITEM:
        item = db.query(RequestItem).filter(RequestItem.id == entity_id).first()
        if item is None:
            return True
        request = db.query(Request).filter(Request.id == item.request_id).first()
        return request is None or can_view_request(db, request, viewer)
    if entity_type is EntityType.COMMENT:
        # A comment is visible exactly when its parent entity is: reacting to a
        # comment on an unpublished campaign (or a private review thread) must
        # stay as hidden as the comment itself. Parents are never comments, so
        # this recurses at most once.
        comment = db.query(Comment).filter(Comment.id == entity_id).first()
        if comment is None:
            return True
        return is_entity_visible(
            db, EntityType(comment.entity_type), comment.entity_id, viewer
        )
    return True
