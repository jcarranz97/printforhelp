"""Domain exceptions for the parts domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class PartNotFoundExceptionError(AppExceptionError):
    """Raised when a Part cannot be found by id."""

    def __init__(self, part_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.PART_NOT_FOUND,
            message=f"Part {part_id} not found.",
            status_code=404,
        )


class NotEffectiveOwnerExceptionError(AppExceptionError):
    """Raised when the caller lacks owner powers on the Part (FR-075)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_EFFECTIVE_OWNER,
            message="This action requires Part owner privileges.",
            status_code=403,
        )


class PartArchiveBlockedExceptionError(AppExceptionError):
    """Raised when archiving a Part still referenced by open Requests (FR-076)."""

    def __init__(self, open_request_count: int) -> None:
        super().__init__(
            error_code=ErrorCode.PART_ARCHIVE_BLOCKED,
            message=(
                "Cannot archive a Part that is still referenced by open Requests."
            ),
            status_code=409,
            details={"open_request_count": open_request_count},
        )


class PartDiscontinuedExceptionError(AppExceptionError):
    """Raised when a Request references a discontinued/inactive Part (FR-075)."""

    def __init__(self, part_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.PART_DISCONTINUED,
            message=f"Part {part_id} is not active and cannot be requested.",
            status_code=409,
        )
