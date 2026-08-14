"""Tests for the printable box label and its manifest page (FR-149)."""

import io
import re
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from app.users.constants import UserRole
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CONTRIB = "/api/v1/contributions"
TRACKING = "/api/v1/tracking"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _center(client: TestClient, headers: dict[str, str], name: str = "Centro") -> str:
    return client.post(
        CENTERS,
        headers=headers,
        json={
            "name": name,
            "address": "Av. 1",
            "country": "VE",
            "city": "Caracas",
            "contact": "x@y.z",
        },
    ).json()["id"]


def _box(client: TestClient, headers: dict[str, str], center_id: str) -> dict[str, Any]:
    return client.post(
        f"{CENTERS}/{center_id}/shipments",
        headers=headers,
        json={"shipment_date": "2026-08-01", "destination": "Caracas, Venezuela"},
    ).json()


def _pack_a_package(
    client: TestClient, headers: dict[str, str], center_id: str, box_id: str
) -> None:
    resource_id = client.post(
        RESOURCES,
        headers=headers,
        json={"name": "Ferula", "source_url": "https://x.io/p.stl"},
    ).json()["id"]
    item_id = client.post(
        REQUESTS,
        headers=headers,
        json={
            "title": "Campaign",
            "items": [{"resource_id": resource_id, "quantity": 100}],
        },
    ).json()["items"][0]["id"]
    contribution = client.post(
        CONTRIB,
        headers=headers,
        json={
            "request_item_id": item_id,
            "collection_center_id": center_id,
            "quantity": 9,
        },
    ).json()
    tracking = client.post(
        f"{TRACKING}/contributions/{contribution['id']}", headers=headers
    ).json()
    resp = client.post(
        f"{CENTERS}/{center_id}/shipments/{box_id}/contents",
        headers=headers,
        json={"tracking_group_id": tracking["group_id"]},
    )
    assert resp.status_code == 201, resp.text


def _pdf_pages(data: bytes) -> int:
    """Count pages by scanning the PDF's page objects.

    Pillow writes PDFs but cannot read them back, so counting has to happen at
    the byte level. Every page Pillow emits carries one ``/Type /Page`` marker
    (the document catalog uses ``/Type /Pages``, which does not match).
    """
    assert data[:4] == b"%PDF"
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


class TestBoxLabel:
    def test_png_renders_for_a_member(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        box = _box(client, h, center_id)
        _pack_a_package(client, h, center_id, box["id"])

        resp = client.get(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/label.png", headers=h
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "image/png"
        assert resp.headers["cache-control"] == "no-store"
        # A4 at 150 dpi.
        assert Image.open(io.BytesIO(resp.content)).size == (1240, 1754)

    def test_pdf_carries_a_manifest_page(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        box = _box(client, h, center_id)
        _pack_a_package(client, h, center_id, box["id"])
        url = f"{CENTERS}/{center_id}/shipments/{box['id']}/label.pdf"

        with_manifest = client.get(url, headers=h)
        assert with_manifest.status_code == 200
        assert with_manifest.headers["content-type"] == "application/pdf"
        without = client.get(f"{url}?manifest=false", headers=h)
        assert _pdf_pages(with_manifest.content) > _pdf_pages(without.content)
        assert _pdf_pages(without.content) == 1

    def test_an_empty_box_still_prints_a_label(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        """Staff label the box before filling it, not after."""
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _box(client, h, center_id)
        resp = client.get(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/label.pdf", headers=h
        )
        assert resp.status_code == 200
        assert _pdf_pages(resp.content) == 2

    def test_a_stranger_cannot_print_the_label(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The label embeds the manifest, which is not public."""
        stranger = make_user(username="stranger")
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _box(client, h, center_id)
        resp = client.get(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/label.png",
            headers=auth_headers(stranger),
        )
        assert resp.status_code == 403

    def test_label_requires_auth(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _box(client, h, center_id)
        resp = client.get(f"{CENTERS}/{center_id}/shipments/{box['id']}/label.png")
        assert resp.status_code in (401, 403)
