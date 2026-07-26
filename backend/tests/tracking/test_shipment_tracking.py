"""Tests for the box QR: token resolution and the downward update waterfall.

Covers FR-137 (a box is scannable), FR-145 (a box update reaches every package
and unit inside it, at any depth) and FR-146 (nothing leaks back upward).
"""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.users.constants import UserRole
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CONTRIB = "/api/v1/contributions"
TRACKING = "/api/v1/tracking"
TRACK = "/api/v1/track"

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


def _box(
    client: TestClient,
    headers: dict[str, str],
    center_id: str,
    destination: str = "Caracas, Venezuela",
) -> dict[str, Any]:
    return client.post(
        f"{CENTERS}/{center_id}/shipments",
        headers=headers,
        json={"shipment_date": "2026-08-01", "destination": destination},
    ).json()


def _package(
    client: TestClient,
    maker_h: dict[str, str],
    center_id: str,
    *,
    qty: int = 3,
    visibility: str | None = None,
) -> dict[str, Any]:
    resource_id = client.post(
        RESOURCES,
        headers=maker_h,
        json={"name": "Ferula", "source_url": "https://x.io/p.stl"},
    ).json()["id"]
    item_id = client.post(
        REQUESTS,
        headers=maker_h,
        json={
            "title": "Campaign",
            "items": [{"resource_id": resource_id, "quantity": 200}],
        },
    ).json()["items"][0]["id"]
    contribution = client.post(
        CONTRIB,
        headers=maker_h,
        json={
            "request_item_id": item_id,
            "collection_center_id": center_id,
            "quantity": qty,
        },
    ).json()
    tracking = client.post(
        f"{TRACKING}/contributions/{contribution['id']}", headers=maker_h
    ).json()
    if visibility is not None:
        client.patch(
            f"{TRACKING}/groups/{tracking['group_id']}",
            headers=maker_h,
            json={"visibility": visibility},
        )
    return {"contribution": contribution, "tracking": tracking}


def _pack(
    client: TestClient,
    headers: dict[str, str],
    center_id: str,
    box_id: str,
    **body: Any,
) -> None:
    resp = client.post(
        f"{CENTERS}/{center_id}/shipments/{box_id}/contents", headers=headers, json=body
    )
    assert resp.status_code == 201, resp.text


def _post_update(
    client: TestClient, token: str, text: str, headers: dict[str, str] | None = None
) -> dict[str, Any]:
    resp = client.post(
        f"{TRACK}/{token}/records",
        headers=headers or {},
        json={"description": text, "tags": []},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestBoxToken:
    def test_a_box_token_resolves_with_its_summary(
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
        pkg = _package(client, h, center_id, qty=6)
        box = _box(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )

        resp = client.get(f"{TRACK}/{box['tracking_token']}", headers=h)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["target_kind"] == "shipment"
        # Contribution-shaped fields are absent for a box.
        assert body["group_id"] is None
        assert body["resource_name"] is None
        assert body["quantity"] is None
        summary = body["shipment"]
        assert summary["destination"] == "Caracas, Venezuela"
        assert summary["package_count"] == 1
        assert summary["units_total"] == 6
        assert summary["can_mark_arrived"] is True

    def test_the_box_qr_image_renders(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _box(client, h, center_id)
        resp = client.get(f"{TRACK}/{box['tracking_token']}/qr.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_quantity_correction_is_refused_on_a_box(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """A box has no unit count of its own — only the packages inside do."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        box = _box(client, h, center_id)
        resp = client.patch(
            f"{TRACK}/{box['tracking_token']}/quantity",
            headers=admin_h,
            json={"quantity": 10},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SHIPMENT_TOKEN_NOT_SUPPORTED"

    def test_confirm_received_on_a_box_marks_it_arrived(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Same physical act — "this reached us" — on the container."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        maker = make_user(username="maker1")
        h, admin_h, maker_h = (
            auth_headers(normal_user),
            auth_headers(admin),
            auth_headers(maker),
        )
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, maker_h, center_id)
        box = _box(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )

        resp = client.post(
            f"{TRACK}/{box['tracking_token']}/confirm-received", headers=h
        )
        assert resp.status_code in (200, 204), resp.text

        mine = client.get(f"{CONTRIB}/me", headers=maker_h).json()
        assert mine[0]["status"] == "received"

    def test_a_guest_may_post_on_a_box(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        """Whoever is holding the box can tell us where it is."""
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _box(client, h, center_id)
        posted = _post_update(client, box["tracking_token"], "Pasó por aduana")
        assert posted["target_kind"] == "shipment"
        assert posted["origin_level"] == "shipment"


class TestWaterfall:
    def test_a_box_update_reaches_the_package_and_every_unit(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The whole point: one QR on the box, news on every piece inside."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, h, center_id, qty=4)
        box = _box(client, h, center_id, destination="Texas")
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )
        _post_update(client, box["tracking_token"], "Salió de California", h)

        # On the package page.
        group_view = client.get(
            f"{TRACK}/{pkg['tracking']['tracking_token']}", headers=h
        ).json()
        box_entries = [
            r for r in group_view["records"] if r["origin_level"] == "shipment"
        ]
        assert len(box_entries) == 1
        assert box_entries[0]["inherited"] is True
        assert box_entries[0]["origin_label"] == "Texas"
        assert box_entries[0]["description"] == "Salió de California"

        # And on each individual unit page.
        for item in pkg["tracking"]["items"]:
            unit_view = client.get(
                f"{TRACK}/{item['tracking_token']}", headers=h
            ).json()
            texts = [r["description"] for r in unit_view["records"]]
            assert "Salió de California" in texts

    def test_a_package_update_rolls_down_to_its_units(
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
        pkg = _package(client, h, center_id, qty=2)
        _post_update(client, pkg["tracking"]["tracking_token"], "Empaquetado", h)

        unit = pkg["tracking"]["items"][0]["tracking_token"]
        view = client.get(f"{TRACK}/{unit}", headers=h).json()
        inherited = [r for r in view["records"] if r["origin_level"] == "group"]
        assert len(inherited) == 1
        assert inherited[0]["inherited"] is True

    def test_an_outer_box_reaches_units_two_levels_down(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The relay case: California box inside the Texas box."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, h, center_id, qty=2)
        inner = _box(client, h, center_id, destination="Texas")
        outer = _box(client, h, center_id, destination="Venezuela")
        _pack(
            client,
            h,
            center_id,
            inner["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )
        _pack(client, h, center_id, outer["id"], child_shipment_id=inner["id"])
        _post_update(client, outer["tracking_token"], "Embarcado a Caracas", h)

        unit = pkg["tracking"]["items"][0]["tracking_token"]
        view = client.get(f"{TRACK}/{unit}", headers=h).json()
        labels = {
            r["origin_label"]
            for r in view["records"]
            if r["origin_level"] == "shipment"
        }
        assert "Venezuela" in labels

    def test_the_inner_box_shows_its_own_route(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        inner = _box(client, h, center_id, destination="Texas")
        outer = _box(client, h, center_id, destination="Venezuela")
        _pack(client, h, center_id, outer["id"], child_shipment_id=inner["id"])

        view = client.get(f"{TRACK}/{inner['tracking_token']}", headers=h).json()
        route = view["shipment"]["route"]
        assert [hop["label"] for hop in route] == ["Venezuela"]

    def test_include_inherited_false_narrows_to_the_scanned_level(
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
        pkg = _package(client, h, center_id, qty=2)
        box = _box(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )
        _post_update(client, box["tracking_token"], "Desde la caja", h)
        unit = pkg["tracking"]["items"][0]["tracking_token"]
        _post_update(client, unit, "Desde la pieza", h)

        full = client.get(f"{TRACK}/{unit}", headers=h).json()
        assert len(full["records"]) == 2
        narrowed = client.get(
            f"{TRACK}/{unit}?include_inherited=false", headers=h
        ).json()
        assert [r["description"] for r in narrowed["records"]] == ["Desde la pieza"]


class TestNoUpwardLeak:
    def test_a_box_timeline_never_shows_its_contents_updates(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """A public box must not publish the updates of a private package."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        maker = make_user(username="maker1")
        h, admin_h, maker_h = (
            auth_headers(normal_user),
            auth_headers(admin),
            auth_headers(maker),
        )
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, maker_h, center_id, qty=2, visibility="private")
        box = _box(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )
        _post_update(
            client, pkg["tracking"]["tracking_token"], "Secreto del maker", maker_h
        )

        guest = client.get(f"{TRACK}/{box['tracking_token']}")
        assert guest.status_code == 200
        assert guest.json()["records"] == []
        assert "Secreto del maker" not in guest.text
        assert pkg["tracking"]["tracking_token"] not in guest.text

    def test_a_box_update_still_reaches_a_private_package_owner(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Rolling down leaks nothing: the page itself is still gated."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        maker = make_user(username="maker1")
        h, admin_h, maker_h = (
            auth_headers(normal_user),
            auth_headers(admin),
            auth_headers(maker),
        )
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, maker_h, center_id, qty=2, visibility="private")
        box = _box(client, h, center_id, destination="Texas")
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )
        _post_update(client, box["tracking_token"], "En camino", h)

        token = pkg["tracking"]["tracking_token"]
        # The maker sees the box news on their private package.
        mine = client.get(f"{TRACK}/{token}", headers=maker_h).json()
        assert "En camino" in [r["description"] for r in mine["records"]]
        # A stranger still cannot open that package at all.
        assert client.get(f"{TRACK}/{token}").status_code == 403
