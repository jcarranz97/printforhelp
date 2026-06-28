"""Domain exceptions for the shipments domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class ShipmentNotFoundExceptionError(AppExceptionError):
    """Raised when a shipment cannot be found by id."""

    def __init__(self, shipment_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.SHIPMENT_NOT_FOUND,
            message=f"Shipment {shipment_id} not found.",
            status_code=404,
        )
