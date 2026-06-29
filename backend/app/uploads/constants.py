"""Constants and error codes for the uploads domain."""

from enum import StrEnum

# Longest edge (px) an uploaded image is downscaled to before storage.
MAX_IMAGE_DIMENSION = 2000


class ErrorCode(StrEnum):
    """Error codes raised by the uploads domain."""

    INVALID_IMAGE = "INVALID_IMAGE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
