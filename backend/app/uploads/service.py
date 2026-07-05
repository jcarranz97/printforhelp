"""Image upload validation, normalization, and storage.

Uploaded bytes are re-encoded with Pillow so embedded metadata (EXIF,
arbitrary chunks) is stripped, the format is restricted to a safe
allowlist, and the image is downscaled to a sane maximum dimension.
"""

import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.storage import get_storage

from .constants import (
    ALLOWED_FILE_EXTENSIONS,
    DEFAULT_FILE_CONTENT_TYPE,
    FILE_CONTENT_TYPES,
    MAX_IMAGE_DIMENSION,
)
from .exceptions import (
    FileTooLargeError,
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedFileTypeError,
)

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


def _download_filename(filename: str | None, extension: str) -> str:
    """Build a safe, readable object-name from an uploaded filename.

    The result becomes the final path segment of the stored key, so a plain
    ``<a href>`` download names the file after the maker's original name (e.g.
    ``Wrist splint.stl`` -> ``Wrist_splint.stl``) instead of a random id.
    Whitespace and path separators collapse to underscores and URL-unsafe
    characters are dropped (preventing path traversal), while unicode letters
    are kept so accented Spanish names stay legible. Falls back to ``model``
    when nothing usable remains. The validated ``extension`` is always
    re-appended.
    """
    stem = Path(filename or "").stem
    cleaned = re.sub(r"[\s/\\]+", "_", stem)
    cleaned = re.sub(r"[^\w.\-]", "", cleaned, flags=re.UNICODE).strip("._-")
    return f"{cleaned or 'model'}.{extension}"


def store_file(data: bytes, filename: str | None) -> str:
    """Validate and persist an uploaded model/source file.

    Unlike images, the bytes are stored verbatim (no re-encoding); the
    extension is allowlisted and the size is capped. Lets makers host their
    designs on PrintForHelp instead of an external site.

    The object is stored under a unique ``files/<uuid>/<original-name>`` key:
    the uuid prefix guarantees uniqueness while the trailing original name
    gives the file a friendly download name (the browser derives it from the
    URL's last path segment).

    Args:
        data: The raw uploaded bytes.
        filename: The original filename (used to derive the extension and the
            friendly download name).

    Returns:
        The public URL of the stored object.

    Raises:
        FileTooLargeError: The payload exceeds ``MAX_UPLOAD_FILE_BYTES``.
        UnsupportedFileTypeError: The extension is not allowlisted.
    """
    if len(data) > settings.MAX_UPLOAD_FILE_BYTES:
        raise FileTooLargeError(settings.MAX_UPLOAD_FILE_BYTES)

    extension = Path(filename or "").suffix.lower().lstrip(".")
    if extension not in ALLOWED_FILE_EXTENSIONS:
        raise UnsupportedFileTypeError(sorted(ALLOWED_FILE_EXTENSIONS))

    content_type = FILE_CONTENT_TYPES.get(extension, DEFAULT_FILE_CONTENT_TYPE)
    key = f"files/{uuid4().hex}/{_download_filename(filename, extension)}"
    return get_storage().save(data, key=key, content_type=content_type)
