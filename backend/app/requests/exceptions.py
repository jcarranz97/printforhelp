"""Domain exceptions for the requests domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class RequestNotFoundExceptionError(AppExceptionError):
    """Raised when a Request cannot be found by id."""

    def __init__(self, request_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.REQUEST_NOT_FOUND,
            message=f"Request {request_id} not found.",
            status_code=404,
        )


class RequestItemNotFoundExceptionError(AppExceptionError):
    """Raised when a RequestItem cannot be found by id."""

    def __init__(self, item_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.REQUEST_ITEM_NOT_FOUND,
            message=f"RequestItem {item_id} not found.",
            status_code=404,
        )


class NotEffectiveRequesterExceptionError(AppExceptionError):
    """Raised when the caller lacks requester powers on the Request (FR-042)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_EFFECTIVE_REQUESTER,
            message="This action requires Request requester privileges.",
            status_code=403,
        )


class RequestNotOpenExceptionError(AppExceptionError):
    """Raised when an edit is attempted on a non-open Request (FR-042)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.REQUEST_NOT_OPEN,
            message="This action is only allowed while the Request is open.",
            status_code=409,
        )


class RequestNeedsItemExceptionError(AppExceptionError):
    """Raised when a Request would be left with no items (FR-119)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.REQUEST_NEEDS_ITEM,
            message="A Request must always have at least one RequestItem.",
            status_code=409,
        )


class ItemHasContributionsExceptionError(AppExceptionError):
    """Raised when removing an item that has active Contributions (FR-123)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.ITEM_HAS_CONTRIBUTIONS,
            message="Cannot remove a RequestItem that has active Contributions.",
            status_code=409,
        )


class ItemRequestMismatchExceptionError(AppExceptionError):
    """Raised when an item id does not belong to the given Request."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.ITEM_REQUEST_MISMATCH,
            message="The RequestItem does not belong to this Request.",
            status_code=404,
        )
