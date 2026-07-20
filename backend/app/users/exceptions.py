"""Domain exceptions for the users domain."""

from datetime import datetime
from uuid import UUID

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class UserNotFoundExceptionError(AppExceptionError):
    """Raised when a user cannot be found by id or username."""

    def __init__(self, identifier: UUID | str) -> None:
        super().__init__(
            error_code=ErrorCode.USER_NOT_FOUND,
            message=f"User {identifier} not found.",
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


class EmailTakenExceptionError(AppExceptionError):
    """Raised when registering with an already-used email (FR-001)."""

    def __init__(self, email: str) -> None:
        super().__init__(
            error_code=ErrorCode.EMAIL_TAKEN,
            message=f"Email '{email}' is already registered.",
            status_code=409,
        )


class UsernameAlreadyChosenExceptionError(AppExceptionError):
    """Raised when a user tries to pick a username after already having one."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.USERNAME_ALREADY_SET,
            message="This account already has a username.",
            status_code=409,
        )


class UsernameChangeTooSoonExceptionError(AppExceptionError):
    """Raised when a user renames again inside the cooldown window."""

    def __init__(self, available_at: datetime) -> None:
        super().__init__(
            error_code=ErrorCode.USERNAME_CHANGE_TOO_SOON,
            message=(
                "You changed your username recently. You can change it again "
                f"after {available_at:%Y-%m-%d}."
            ),
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


class UnknownFlagExceptionError(AppExceptionError):
    """Raised when a flag key is not in the registry (``FLAG_REGISTRY``)."""

    def __init__(self, key: str) -> None:
        super().__init__(
            error_code=ErrorCode.UNKNOWN_FLAG,
            message=f"Unknown user flag '{key}'.",
            status_code=422,
        )


class FlagNotSelfAssignableExceptionError(AppExceptionError):
    """Raised when a user tries to self-set a flag only admins may grant."""

    def __init__(self, key: str) -> None:
        super().__init__(
            error_code=ErrorCode.FLAG_NOT_SELF_ASSIGNABLE,
            message=f"The flag '{key}' cannot be set by the user directly.",
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
