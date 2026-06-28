"""Domain exceptions for the auth domain."""

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class InvalidCredentialsExceptionError(AppExceptionError):
    """Raised on a failed login (unknown user or wrong password)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message="Invalid username or password.",
            status_code=401,
        )


class InvalidTokenExceptionError(AppExceptionError):
    """Raised when a bearer token is missing, malformed, or expired."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_TOKEN,
            message="Invalid or expired authentication token.",
            status_code=401,
        )


class InactiveUserExceptionError(AppExceptionError):
    """Raised when an inactive account attempts to authenticate (FR-013)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INACTIVE_USER,
            message="This account is inactive.",
            status_code=403,
        )


class WeakPasswordExceptionError(AppExceptionError):
    """Raised when a password fails the strength policy (FR-002)."""

    def __init__(self, message: str) -> None:
        super().__init__(
            error_code=ErrorCode.WEAK_PASSWORD,
            message=message,
            status_code=400,
        )


class IncorrectPasswordExceptionError(AppExceptionError):
    """Raised when the supplied current password is wrong (FR-005)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INCORRECT_PASSWORD,
            message="Current password is incorrect.",
            status_code=400,
        )
