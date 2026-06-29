"""Domain exceptions for the uploads domain."""

from app.exceptions import AppExceptionError

from .constants import ErrorCode


class InvalidImageError(AppExceptionError):
    """Raised when an upload is not a supported image."""

    def __init__(self) -> None:
        super().__init__(
            error_code=ErrorCode.INVALID_IMAGE,
            message="Uploaded file is not a valid PNG, JPEG, or WebP image.",
            status_code=400,
        )


class ImageTooLargeError(AppExceptionError):
    """Raised when an upload exceeds the configured size cap."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            error_code=ErrorCode.IMAGE_TOO_LARGE,
            message="Uploaded image exceeds the maximum allowed size.",
            status_code=413,
            details={"max_bytes": max_bytes},
        )
