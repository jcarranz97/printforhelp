"""Enums and error codes for the shipments domain."""

from enum import StrEnum


class ShipmentStatus(StrEnum):
    """Lifecycle status of a Collection Center shipment (FR-128).

    A shipment is the planned dispatch of collected aid from a Collection
    Center to where it is needed. ``receiving`` means the center is still
    accepting packages for this shipment; ``closed`` means it has been
    dispatched (no longer accepting); ``cancelled`` means it was called off.
    """

    RECEIVING = "receiving"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ErrorCode(StrEnum):
    """Error codes raised by the shipments domain."""

    SHIPMENT_NOT_FOUND = "SHIPMENT_NOT_FOUND"
