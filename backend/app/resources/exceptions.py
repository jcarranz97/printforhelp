"""Domain exceptions for the resources domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class ResourceNotFoundExceptionError(AppExceptionError):
    """Raised when a Resource cannot be found by id."""

    def __init__(self, resource_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=f"Resource {resource_id} not found.",
            status_code=404,
        )


class NotEffectiveOwnerExceptionError(AppExceptionError):
    """Raised when the caller lacks owner powers on the Resource (FR-075)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_EFFECTIVE_OWNER,
            message="This action requires Resource owner privileges.",
            status_code=403,
        )


class ResourceArchiveBlockedExceptionError(AppExceptionError):
    """Raised when archiving a Resource still referenced by open Requests (FR-076)."""

    def __init__(self, open_request_count: int) -> None:
        super().__init__(
            error_code=ErrorCode.RESOURCE_ARCHIVE_BLOCKED,
            message=(
                "Cannot archive a Resource that is still referenced by open Requests."
            ),
            status_code=409,
            details={"open_request_count": open_request_count},
        )


class ResourceDiscontinuedExceptionError(AppExceptionError):
    """Raised when a Request references a discontinued/inactive Resource (FR-075)."""

    def __init__(self, resource_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.RESOURCE_DISCONTINUED,
            message=f"Resource {resource_id} is not active and cannot be requested.",
            status_code=409,
        )


class SourceUrlRequiredExceptionError(AppExceptionError):
    """Raised when a ``print_3d`` Resource is missing its ``source_url``."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.SOURCE_URL_REQUIRED,
            message="A 3D-print resource requires a source_url (the STL/model link).",
            status_code=422,
        )
