"""Domain exceptions for the item-tracking domain.

All inherit :class:`AppExceptionError`; the global handler renders them into
the standard ``{success, error: {code, message}}`` envelope.
"""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class TrackingNotFoundExceptionError(AppExceptionError):
    """No tracking group/item/token matched the lookup (404)."""

    def __init__(self, identifier: UUID | str) -> None:
        super().__init__(
            error_code=ErrorCode.TRACKING_NOT_FOUND,
            message=f"No tracking found for {identifier}.",
            status_code=404,
        )


class TrackingAlreadyExistsExceptionError(AppExceptionError):
    """A Contribution already has a tracking group (409)."""

    def __init__(self, contribution_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.TRACKING_ALREADY_EXISTS,
            message=f"Contribution {contribution_id} already has tracking.",
            status_code=409,
        )


class TrackingForbiddenExceptionError(AppExceptionError):
    """The caller may not view or manage this tracking (403)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.TRACKING_FORBIDDEN,
            message="You do not have access to this tracking.",
            status_code=403,
        )


class RecordNotFoundExceptionError(AppExceptionError):
    """The tracking record does not exist (404)."""

    def __init__(self, record_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.RECORD_NOT_FOUND,
            message=f"Tracking record {record_id} not found.",
            status_code=404,
        )


class RecordEditForbiddenExceptionError(AppExceptionError):
    """The caller may not edit this record's tags (403)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.RECORD_EDIT_FORBIDDEN,
            message="You may not edit this record.",
            status_code=403,
        )


class ContributorMessageNotFoundExceptionError(AppExceptionError):
    """No saved contributor message matched for this user (404)."""

    def __init__(self, message_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.MESSAGE_NOT_FOUND,
            message=f"Saved message {message_id} not found.",
            status_code=404,
        )
