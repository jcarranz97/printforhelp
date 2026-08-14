"""Domain exceptions for the shipments domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import MAX_SHIPMENT_DEPTH, ErrorCode, ShipmentStatus


class ShipmentNotFoundExceptionError(AppExceptionError):
    """Raised when a shipment cannot be found by id."""

    def __init__(self, shipment_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.SHIPMENT_NOT_FOUND,
            message=f"Shipment {shipment_id} not found.",
            status_code=404,
        )


class ShipmentContentNotFoundExceptionError(AppExceptionError):
    """Raised when a manifest line cannot be found on this shipment."""

    def __init__(self, content_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.SHIPMENT_CONTENT_NOT_FOUND,
            message=f"Shipment content {content_id} not found.",
            status_code=404,
        )


class ShipmentLockedExceptionError(AppExceptionError):
    """Raised when packing or unpacking a shipment that is sealed or in flight.

    Contents may only change while the box is open at one end of its journey
    (``receiving`` or ``arrived``), so a manifest always describes what
    physically travelled.
    """

    def __init__(self, status: ShipmentStatus) -> None:
        super().__init__(
            error_code=ErrorCode.SHIPMENT_LOCKED,
            message=(
                f"Contents cannot be changed while the shipment is '{status.value}'."
            ),
            status_code=409,
        )


class ShipmentCycleExceptionError(AppExceptionError):
    """Raised when nesting a shipment would make it contain itself."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.SHIPMENT_CYCLE,
            message="A shipment cannot be packed into itself or into its own contents.",
            status_code=409,
        )


class ShipmentTooDeepExceptionError(AppExceptionError):
    """Raised when nesting would push the containment chain past its limit."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.SHIPMENT_TOO_DEEP,
            message=(
                f"Shipments cannot be nested more than {MAX_SHIPMENT_DEPTH} deep."
            ),
            status_code=409,
        )


class AlreadyPackedExceptionError(AppExceptionError):
    """Raised when packing something that already rides in another shipment."""

    def __init__(self, holder_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.ALREADY_PACKED,
            message=f"Already packed into shipment {holder_id}; unpack it first.",
            status_code=409,
        )


class InvalidShipmentTransitionExceptionError(AppExceptionError):
    """Raised when a status change is not allowed from the current status."""

    def __init__(self, current: ShipmentStatus, target: ShipmentStatus) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_SHIPMENT_TRANSITION,
            message=f"Cannot move a shipment from '{current.value}' to "
            f"'{target.value}'.",
            status_code=409,
        )


class ShipmentTokenNotSupportedExceptionError(AppExceptionError):
    """Raised for a scan action that makes no sense on a box token.

    Correcting a unit count, for instance: a box has no units of its own, only
    the packages inside it, each with its own count.
    """

    def __init__(self, action: str) -> None:
        super().__init__(
            error_code=ErrorCode.SHIPMENT_TOKEN_NOT_SUPPORTED,
            message=f"'{action}' is not available on a shipment token.",
            status_code=409,
        )
