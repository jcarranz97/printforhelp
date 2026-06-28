"""Shipment HTTP routes, nested under a Collection Center (FR-127..130)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentActiveUser

from . import schemas, service

router = APIRouter(
    prefix="/collection-centers/{collection_center_id}/shipments",
    tags=["shipments"],
)

DatabaseDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[schemas.ShipmentResponse])
async def list_shipments(
    collection_center_id: UUID,
    db: DatabaseDep,
) -> list[schemas.ShipmentResponse]:
    """List a center's shipments (public — always visible, FR-130)."""
    shipments = service.list_shipments(db, collection_center_id)
    return [schemas.ShipmentResponse.model_validate(s) for s in shipments]


@router.post(
    "", response_model=schemas.ShipmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_shipment(
    collection_center_id: UUID,
    payload: schemas.ShipmentCreate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentResponse:
    """Create a shipment (effective member or maintainer/admin, FR-129)."""
    shipment = service.create_shipment(db, collection_center_id, payload, actor)
    return schemas.ShipmentResponse.model_validate(shipment)


@router.patch("/{shipment_id}", response_model=schemas.ShipmentResponse)
async def update_shipment(
    collection_center_id: UUID,
    shipment_id: UUID,
    payload: schemas.ShipmentUpdate,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> schemas.ShipmentResponse:
    """Edit a shipment, including its status (FR-129)."""
    shipment = service.update_shipment(
        db, collection_center_id, shipment_id, payload, actor
    )
    return schemas.ShipmentResponse.model_validate(shipment)


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipment(
    collection_center_id: UUID,
    shipment_id: UUID,
    actor: CurrentActiveUser,
    db: DatabaseDep,
) -> None:
    """Soft-delete a shipment (effective member or maintainer/admin)."""
    service.delete_shipment(db, collection_center_id, shipment_id, actor)
