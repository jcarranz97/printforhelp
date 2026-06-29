"""File storage abstraction for uploaded media.

v1 ships a local-disk backend; an S3-compatible backend (MinIO / R2 /
S3 via boto3) can drop in later behind the same :class:`Storage`
interface without touching the upload endpoint, schemas, or frontend.
"""

from pathlib import Path
from typing import Protocol

from app.config import settings


class Storage(Protocol):
    """Pluggable blob store: persist bytes and return a public URL."""

    def save(self, data: bytes, *, key: str, content_type: str) -> str:
        """Persist ``data`` under ``key`` and return a browser URL."""
        ...

    def delete(self, key: str) -> None:
        """Remove the object stored at ``key`` (no-op when absent)."""
        ...


class LocalDiskStorage:
    """Store objects on the local filesystem under ``MEDIA_ROOT``.

    Files are served back by the ``/media`` static mount in
    :mod:`app.main` (local backend only).
    """

    def save(self, data: bytes, *, key: str, content_type: str) -> str:  # noqa: ARG002
        """Write ``data`` to ``MEDIA_ROOT/key`` and return its public URL."""
        path = Path(settings.MEDIA_ROOT) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"{settings.MEDIA_BASE_URL}/media/{key}"

    def delete(self, key: str) -> None:
        """Delete ``MEDIA_ROOT/key`` if it exists."""
        Path(settings.MEDIA_ROOT, key).unlink(missing_ok=True)


def get_storage() -> Storage:
    """Return the storage backend selected by ``STORAGE_BACKEND``."""
    if settings.STORAGE_BACKEND == "local":
        return LocalDiskStorage()
    # TODO(s3): add a boto3-backed ``S3Storage`` implementing ``Storage``
    # and return it here when ``STORAGE_BACKEND == "s3"``. The interface
    # above is identical, so the upload endpoint stays unchanged.
    raise NotImplementedError(
        f"Unsupported STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}"
    )
