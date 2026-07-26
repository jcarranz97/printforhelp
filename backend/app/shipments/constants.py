"""Enums, transitions, and error codes for the shipments domain."""

from enum import StrEnum

# How deep a box may be nested inside other boxes. Real relay chains are two
# to four hops (local center -> regional hub -> destination country), so this
# is a runaway guard, not a limit anyone should feel. It also bounds every
# ancestor/descendant walk in ``service.py``, which is what keeps a corrupted
# containment graph from looping forever.
MAX_SHIPMENT_DEPTH = 5


class ShipmentStatus(StrEnum):
    """Lifecycle status of a Collection Center shipment (FR-128, FR-141).

    A shipment is a physical box of collected aid dispatched from a Collection
    Center. ``receiving`` means the center is still packing it (the only state
    in which contents may be edited); ``in_transit`` means it has left;
    ``arrived`` means it reached its destination, which is what bulk-receives
    everything inside; ``closed`` means it is finished with; ``cancelled``
    means it was called off.

    ``closed`` predates the box model, where it meant "dispatched, no longer
    accepting". It is kept as a terminal state — and reachable straight from
    ``receiving`` — so the announcement-style shipments the centers already
    use keep working untouched.
    """

    RECEIVING = "receiving"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# Legal ``status`` transitions (FR-141). Anything absent is a 409.
SHIPMENT_TRANSITIONS: dict[ShipmentStatus, tuple[ShipmentStatus, ...]] = {
    ShipmentStatus.RECEIVING: (
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.ARRIVED,
        ShipmentStatus.CLOSED,
        ShipmentStatus.CANCELLED,
    ),
    ShipmentStatus.IN_TRANSIT: (
        ShipmentStatus.ARRIVED,
        ShipmentStatus.CANCELLED,
    ),
    ShipmentStatus.ARRIVED: (ShipmentStatus.CLOSED,),
    ShipmentStatus.CLOSED: (),
    ShipmentStatus.CANCELLED: (),
}

# Contents may only be packed or unpacked while the box is open at one end of
# its journey: ``receiving`` (still being filled at the origin) or ``arrived``
# (sitting open at the destination, where a relay center takes packages out to
# repack them into the next box). Sealed and in-flight boxes are frozen, so a
# manifest always describes what physically travelled.
PACKABLE_STATUSES = (ShipmentStatus.RECEIVING, ShipmentStatus.ARRIVED)

# States a box can arrive from. ``receiving`` is included because a center
# that walks a box across town never marks it in transit first.
ARRIVABLE_STATUSES = (ShipmentStatus.RECEIVING, ShipmentStatus.IN_TRANSIT)


class ErrorCode(StrEnum):
    """Error codes raised by the shipments domain."""

    SHIPMENT_NOT_FOUND = "SHIPMENT_NOT_FOUND"
    SHIPMENT_CONTENT_NOT_FOUND = "SHIPMENT_CONTENT_NOT_FOUND"
    SHIPMENT_LOCKED = "SHIPMENT_LOCKED"
    SHIPMENT_CYCLE = "SHIPMENT_CYCLE"
    SHIPMENT_TOO_DEEP = "SHIPMENT_TOO_DEEP"
    ALREADY_PACKED = "ALREADY_PACKED"
    INVALID_SHIPMENT_TRANSITION = "INVALID_SHIPMENT_TRANSITION"
    SHIPMENT_TOKEN_NOT_SUPPORTED = "SHIPMENT_TOKEN_NOT_SUPPORTED"
