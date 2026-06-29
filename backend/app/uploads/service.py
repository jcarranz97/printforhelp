"""Image upload validation, normalization, and storage.

Uploaded bytes are re-encoded with Pillow so embedded metadata (EXIF,
arbitrary chunks) is stripped, the format is restricted to a safe
allowlist, and the image is downscaled to a sane maximum dimension.
"""

from io import BytesIO
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.storage import get_storage

from .constants import MAX_IMAGE_DIMENSION
from .exceptions import ImageTooLargeError, InvalidImageError

# Pillow format -> (file extension, response content type, save format).
# Acts as the allowlist: anything Pillow opens with a different format is
# rejected as an invalid image.
_FORMAT_SPEC: dict[str, tuple[str, str, str]] = {
    "PNG": ("png", "image/png", "PNG"),
    "JPEG": ("jpg", "image/jpeg", "JPEG"),
    "WEBP": ("webp", "image/webp", "WEBP"),
}


def store_image(data: bytes) -> str:
    """Validate, normalize, and persist an uploaded image.

    Args:
        data: The raw uploaded bytes.

    Returns:
        The public URL of the stored object.

    Raises:
        ImageTooLargeError: The payload exceeds ``MAX_IMAGE_BYTES``.
        InvalidImageError: The payload is not a supported image.
    """
    if len(data) > settings.MAX_IMAGE_BYTES:
        raise ImageTooLargeError(settings.MAX_IMAGE_BYTES)

    try:
        # ``verify`` confirms integrity but leaves the image unusable, so
        # reopen a fresh handle for the actual transforms.
        Image.open(BytesIO(data)).verify()
        image = Image.open(BytesIO(data))
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError from exc

    spec = _FORMAT_SPEC.get((image.format or "").upper())
    if spec is None:
        raise InvalidImageError
    extension, content_type, save_format = spec

    # JPEG cannot store alpha or palette modes; normalize before saving.
    if save_format == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

    buffer = BytesIO()
    image.save(buffer, format=save_format)

    key = f"images/{uuid4().hex}.{extension}"
    return get_storage().save(buffer.getvalue(), key=key, content_type=content_type)
