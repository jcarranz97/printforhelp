"""Domain exceptions for the collection centers domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class CollectionCenterNotFoundExceptionError(AppExceptionError):
    """Raised when a collection center cannot be found by id."""

    def __init__(self, collection_center_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.COLLECTION_CENTER_NOT_FOUND,
            message=f"Collection Center {collection_center_id} not found.",
            status_code=404,
        )


class NotEffectiveOwnerExceptionError(AppExceptionError):
    """Raised when the caller lacks owner powers on the center (FR-079)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_EFFECTIVE_OWNER,
            message="This action requires Collection Center owner privileges.",
            status_code=403,
        )


class NotEffectiveMemberExceptionError(AppExceptionError):
    """Raised when the caller lacks member powers on the center (FR-031)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_EFFECTIVE_MEMBER,
            message="This action requires Collection Center membership.",
            status_code=403,
        )


class CCArchiveBlockedExceptionError(AppExceptionError):
    """Raised when archiving a center with open Contributions (FR-079)."""

    def __init__(self, open_contribution_count: int) -> None:
        super().__init__(
            error_code=ErrorCode.CC_ARCHIVE_BLOCKED,
            message=(
                "Cannot archive a Collection Center that still has open "
                "Contributions routed to it."
            ),
            status_code=409,
            details={"open_contribution_count": open_contribution_count},
        )


class NotContributorExceptionError(AppExceptionError):
    """Raised when the target user is not a contributor of the center."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_CONTRIBUTOR,
            message="The target user is not a contributor of this Collection Center.",
            status_code=409,
        )
