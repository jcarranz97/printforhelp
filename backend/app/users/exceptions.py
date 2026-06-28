"""Domain exceptions for the users domain."""

from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class UserNotFoundExceptionError(AppExceptionError):
    """Raised when a user cannot be found by id."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(
            error_code=ErrorCode.USER_NOT_FOUND,
            message=f"User {user_id} not found.",
            status_code=404,
        )


class UsernameTakenExceptionError(AppExceptionError):
    """Raised when creating a user with an already-used username."""

    def __init__(self, username: str) -> None:
        super().__init__(
            error_code=ErrorCode.USERNAME_TAKEN,
            message=f"Username '{username}' is already taken.",
            status_code=409,
        )


class RoleRequiredExceptionError(AppExceptionError):
    """Raised when the caller lacks the required role."""

    def __init__(self, required_role: str = "admin") -> None:
        super().__init__(
            error_code=ErrorCode.ROLE_REQUIRED,
            message=f"This action requires the '{required_role}' role.",
            status_code=403,
        )


class LockoutProtectionExceptionError(AppExceptionError):
    """Raised when an action would remove the last active admin (FR-014)."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.LOCKOUT_PROTECTION,
            message=(
                "Cannot demote or deactivate the last active admin. "
                "Promote another admin first."
            ),
            status_code=403,
        )
