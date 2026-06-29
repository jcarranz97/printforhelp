"""Enums and error codes for the resources domain."""

from enum import StrEnum


class ResourceStatus(StrEnum):
    """Catalog status of a Resource (FR-075)."""

    ACTIVE = "active"
    DISCONTINUED = "discontinued"


class ResourceCategory(StrEnum):
    """Kind of aid a catalog Resource represents.

    v1 only creates and surfaces ``PRINT_3D`` (3D-printable designs); the
    remaining values are defined now so the generic-supply catalog (food,
    water, medicine, etc.) needs no schema migration when those flows are
    turned on later. ``PRINT_3D`` resources require a ``source_url`` (the
    STL/model link); the other categories make it optional. Service-style
    needs (volunteers, lodging) that do not fit the quantity-of-goods model
    are deliberately out of scope and would need their own follow-up.
    """

    PRINT_3D = "print_3d"
    FOOD = "food"
    WATER = "water"
    MEDICINE = "medicine"
    HYGIENE = "hygiene"
    CLOTHING = "clothing"
    TOOLS = "tools"
    OTHER = "other"


class ErrorCode(StrEnum):
    """Error codes raised by the resources domain."""

    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    NOT_EFFECTIVE_OWNER = "NOT_EFFECTIVE_OWNER"
    RESOURCE_ARCHIVE_BLOCKED = "RESOURCE_ARCHIVE_BLOCKED"
    RESOURCE_DISCONTINUED = "RESOURCE_DISCONTINUED"
    SOURCE_URL_REQUIRED = "SOURCE_URL_REQUIRED"
