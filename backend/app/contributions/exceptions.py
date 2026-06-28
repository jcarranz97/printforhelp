"""Domain exceptions for the contributions domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class ContributionNotFoundExceptionError(AppExceptionError):
    """Raised when a Contribution cannot be found by id."""

    def __init__(self, contribution_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.CONTRIBUTION_NOT_FOUND,
            message=f"Contribution {contribution_id} not found.",
            status_code=404,
        )


class NotTheMakerExceptionError(AppExceptionError):
    """Raised when a non-maker tries to advance a Contribution (FR-053)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_THE_MAKER,
            message="Only the maker can perform this action.",
            status_code=403,
        )


class InvalidTransitionExceptionError(AppExceptionError):
    """Raised when a lifecycle transition is not allowed from the current state."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_TRANSITION,
            message=f"Cannot transition a Contribution from {current} to {target}.",
            status_code=409,
        )


class NotReceiverExceptionError(AppExceptionError):
    """Raised when the caller cannot confirm receipt at the center (FR-056)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.NOT_RECEIVER,
            message=(
                "Only an effective member of the target Collection Center "
                "(or a maintainer/admin) can confirm receipt."
            ),
            status_code=403,
        )


class RequestItemNotOpenExceptionError(AppExceptionError):
    """Raised when claiming against a non-open RequestItem (FR-050)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.REQUEST_ITEM_NOT_OPEN,
            message="Contributions can only be created on an open RequestItem.",
            status_code=409,
        )


class CenterNotAvailableExceptionError(AppExceptionError):
    """Raised when the target center is not verified+active (FR-064)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.CENTER_NOT_AVAILABLE,
            message=(
                "The target Collection Center must be verified and active to "
                "accept Contributions."
            ),
            status_code=409,
        )


class ContributionLockedExceptionError(AppExceptionError):
    """Raised when editing a Contribution past ``claimed`` (FR-057)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.CONTRIBUTION_LOCKED,
            message="A Contribution can only be edited while it is claimed.",
            status_code=409,
        )
