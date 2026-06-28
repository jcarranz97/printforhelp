"""Constants and error codes for the auth domain."""

from enum import StrEnum

# Password strength policy (FR-002): at least 8 characters and must
# contain at least one letter and one digit.
MIN_PASSWORD_LENGTH = 8


class ErrorCode(StrEnum):
    """Error codes raised by the auth domain."""

    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_TOKEN = "INVALID_TOKEN"
    INACTIVE_USER = "INACTIVE_USER"
    WEAK_PASSWORD = "WEAK_PASSWORD"
    INCORRECT_PASSWORD = "INCORRECT_PASSWORD"
    REGISTRATION_DISABLED = "REGISTRATION_DISABLED"
