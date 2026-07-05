"""Domain exceptions for the notifications domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class InvalidWatchTargetExceptionError(AppExceptionError):
    """Raised when a watch targets a non-existent entity."""

    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_WATCH_TARGET,
            message=f"No {entity_type} found with id {entity_id}.",
            status_code=404,
        )


class InvalidMarkReadRequestExceptionError(AppExceptionError):
    """Raised when a mark-read request supplies neither ids nor all=true."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_MARK_READ_REQUEST,
            message="Provide either ids or all=true to mark notifications read.",
            status_code=422,
        )
