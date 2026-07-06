"""Tests for the image upload endpoint and storage backend."""

from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.storage import LocalDiskStorage, get_storage
from app.users.models import User

UPLOAD_URL = "/api/v1/uploads/images"
FILES_URL = "/api/v1/uploads/files"


@pytest.fixture
def media_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point storage at an isolated temp directory for the test."""
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    return tmp_path


def _image_bytes(
    fmt: str = "PNG",
    *,
    mode: str = "RGB",
    size: tuple[int, int] = (10, 10),
) -> bytes:
    buffer = BytesIO()
    Image.new(mode, size, color=0).save(buffer, format=fmt)
    return buffer.getvalue()


def _key_from_url(url: str) -> str:
    return url.split("/media/", 1)[1]


@pytest.mark.parametrize(
    ("fmt", "content_type", "extension"),
    [
        ("PNG", "image/png", "png"),
        ("JPEG", "image/jpeg", "jpg"),
        ("WEBP", "image/webp", "webp"),
    ],
)
def test_upload_image_stores_file_and_returns_url(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
    fmt: str,
    content_type: str,
    extension: str,
) -> None:
    response = client.post(
        UPLOAD_URL,
        files={"file": (f"design.{extension}", _image_bytes(fmt), content_type)},
        headers=auth_headers(normal_user),
    )

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith(f"{settings.MEDIA_BASE_URL}/media/images/")
    assert url.endswith(f".{extension}")
    assert (media_root / _key_from_url(url)).exists()


def test_upload_heic_photo_is_reencoded_to_jpeg(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
) -> None:
    """iPhone photos arrive as HEIC; they must be accepted and stored as JPEG."""
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color=0).save(buffer, format="HEIF")
    response = client.post(
        UPLOAD_URL,
        files={"file": ("photo.heic", buffer.getvalue(), "image/heic")},
        headers=auth_headers(normal_user),
    )

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.endswith(".jpg")
    stored = Image.open(media_root / _key_from_url(url))
    assert stored.format == "JPEG"


def test_upload_requires_auth(client: TestClient, media_root: Path) -> None:
    response = client.post(
        UPLOAD_URL,
        files={"file": ("design.png", _image_bytes(), "image/png")},
    )
    assert response.status_code == 401


def test_upload_rejects_non_image(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
) -> None:
    response = client.post(
        UPLOAD_URL,
        files={"file": ("design.png", b"definitely not an image", "image/png")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_upload_rejects_unsupported_format(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
) -> None:
    response = client.post(
        UPLOAD_URL,
        files={"file": ("design.bmp", _image_bytes("BMP"), "image/bmp")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_upload_rejects_oversize(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "MAX_IMAGE_BYTES", 10)
    response = client.post(
        UPLOAD_URL,
        files={"file": ("design.png", _image_bytes(), "image/png")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"
    assert response.json()["error"]["details"]["max_bytes"] == 10


def test_upload_downscales_large_image(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
) -> None:
    response = client.post(
        UPLOAD_URL,
        files={"file": ("big.png", _image_bytes(size=(3000, 1500)), "image/png")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 201
    stored = Image.open(media_root / _key_from_url(response.json()["url"]))
    assert max(stored.size) <= 2000


def test_upload_converts_cmyk_jpeg(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
) -> None:
    response = client.post(
        UPLOAD_URL,
        files={"file": ("cmyk.jpg", _image_bytes("JPEG", mode="CMYK"), "image/jpeg")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 201
    stored = Image.open(media_root / _key_from_url(response.json()["url"]))
    assert stored.mode == "RGB"


def test_upload_file_stores_and_returns_url(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
) -> None:
    response = client.post(
        FILES_URL,
        files={"file": ("model.stl", b"solid x\nendsolid x", "model/stl")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith(f"{settings.MEDIA_BASE_URL}/media/files/")
    assert url.endswith(".stl")
    assert (media_root / _key_from_url(url)).read_bytes() == b"solid x\nendsolid x"


def test_upload_file_requires_auth(client: TestClient, media_root: Path) -> None:
    response = client.post(
        FILES_URL,
        files={"file": ("model.stl", b"x", "model/stl")},
    )
    assert response.status_code == 401


def test_upload_file_rejects_unsupported_type(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
) -> None:
    response = client.post(
        FILES_URL,
        files={"file": ("design.exe", b"x", "application/octet-stream")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_file_rejects_oversize(
    client: TestClient,
    auth_headers: Callable[[User], dict[str, str]],
    normal_user: User,
    media_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "MAX_UPLOAD_FILE_BYTES", 5)
    response = client.post(
        FILES_URL,
        files={"file": ("model.stl", b"way too big", "model/stl")},
        headers=auth_headers(normal_user),
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert response.json()["error"]["details"]["max_bytes"] == 5


def test_get_storage_returns_local_backend() -> None:
    assert isinstance(get_storage(), LocalDiskStorage)


def test_get_storage_rejects_unknown_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    with pytest.raises(NotImplementedError):
        get_storage()


def test_local_disk_storage_save_and_delete(media_root: Path) -> None:
    storage = LocalDiskStorage()
    url = storage.save(b"hello", key="resources/x.png", content_type="image/png")

    assert url == f"{settings.MEDIA_BASE_URL}/media/resources/x.png"
    assert (media_root / "resources" / "x.png").read_bytes() == b"hello"

    storage.delete("resources/x.png")
    assert not (media_root / "resources" / "x.png").exists()
    # Deleting a missing key is a no-op.
    storage.delete("resources/x.png")
