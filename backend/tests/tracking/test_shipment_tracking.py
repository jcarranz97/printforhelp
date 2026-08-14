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

    def test_unit_updates_still_roll_up_to_their_package(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The pre-existing roll-up, proved to survive the box waterfall.

        A package timeline is the fullest view there is: its own updates, its
        units' rolling up, and the enclosing box's rolling down. Regression
        guard for the item-union being lost when the ancestor-union was added.
        """
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, h, center_id, qty=3)
        box = _box(client, h, center_id, destination="Texas")
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )

        unit = pkg["tracking"]["items"][0]
        _post_update(client, unit["tracking_token"], "Pieza 1 lista", h)
        _post_update(client, pkg["tracking"]["tracking_token"], "Aporte listo", h)
        _post_update(client, box["tracking_token"], "Salió la caja", h)

        view = client.get(
            f"{TRACK}/{pkg['tracking']['tracking_token']}", headers=h
        ).json()
        by_level = {r["origin_level"]: r for r in view["records"]}
        assert set(by_level) == {"item", "group", "shipment"}
        # The unit entry keeps its own identity, labelled by unit number.
        assert by_level["item"]["description"] == "Pieza 1 lista"
        assert by_level["item"]["item_sequence"] == unit["sequence"]
        assert by_level["item"]["target_token"] == unit["tracking_token"]
        # Rolling *up* is not "inherited" — the package owns its units.
        assert by_level["item"]["inherited"] is False
        # Only the box entry, which came from above, is badged as inherited.
        assert by_level["shipment"]["inherited"] is True

        # The existing opt-out still narrows to package-level updates.
        narrowed = client.get(
            f"{TRACK}/{pkg['tracking']['tracking_token']}"
            "?include_item_updates=false&include_inherited=false",
            headers=h,
        ).json()
        assert [r["description"] for r in narrowed["records"]] == ["Aporte listo"]

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


class TestPackFromScan:
    """Scanning a QR offers the centre's own open boxes to file it into."""

    def test_a_center_member_is_offered_their_open_boxes(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
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
        box = _box(client, h, center_id, destination="Mérida")

        view = client.get(
            f"{TRACK}/{pkg['tracking']['tracking_token']}", headers=h
        ).json()
        packing = view["packing"]
        assert packing is not None
        assert packing["current_shipment_id"] is None
        assert [o["shipment_id"] for o in packing["options"]] == [box["id"]]
        assert "Mérida" in packing["options"][0]["label"]

    def test_guests_and_makers_are_offered_nothing(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The packing UI belongs to centre staff, not to whoever scans."""
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
        _box(client, h, center_id)
        token = pkg["tracking"]["tracking_token"]

        assert client.get(f"{TRACK}/{token}").json()["packing"] is None
        assert client.get(f"{TRACK}/{token}", headers=maker_h).json()["packing"] is None

    def test_scanning_a_unit_offers_boxes_too(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Staff scan whatever faces them; a unit files its whole package."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, h, center_id, qty=3)
        _box(client, h, center_id)

        unit = pkg["tracking"]["items"][0]["tracking_token"]
        packing = client.get(f"{TRACK}/{unit}", headers=h).json()["packing"]
        assert len(packing["options"]) == 1

    def test_an_already_packed_group_reports_its_box(
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
        pkg = _package(client, h, center_id)
        box = _box(client, h, center_id, destination="Mérida")
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )

        packing = client.get(
            f"{TRACK}/{pkg['tracking']['tracking_token']}", headers=h
        ).json()["packing"]
        assert packing["current_shipment_id"] == box["id"]
        assert packing["current_shipment_label"] == "Mérida"
        assert packing["current_shipment_token"] == box["tracking_token"]

    def test_sealed_boxes_are_not_offered(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Only boxes still open at one end of their journey can take packages."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, h, center_id)
        box = _box(client, h, center_id)
        client.post(f"{CENTERS}/{center_id}/shipments/{box['id']}/dispatch", headers=h)

        view = client.get(
            f"{TRACK}/{pkg['tracking']['tracking_token']}", headers=h
        ).json()
        assert view["packing"] is None

    def test_scanning_a_box_never_offers_itself_or_its_contents(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        """A cycle is filtered out of the picker, not rejected after the fact."""
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        outer = _box(client, h, center_id, destination="Venezuela")
        inner = _box(client, h, center_id, destination="Texas")
        spare = _box(client, h, center_id, destination="Otro")
        _pack(client, h, center_id, outer["id"], child_shipment_id=inner["id"])

        packing = client.get(f"{TRACK}/{outer['tracking_token']}", headers=h).json()[
            "packing"
        ]
        offered = {o["shipment_id"] for o in packing["options"]}
        assert outer["id"] not in offered
        assert inner["id"] not in offered
        assert spare["id"] in offered

    def test_packing_from_the_scan_page_actually_works(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """End to end: read the option, use it, see the result reflected back."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, h, center_id, qty=4)
        box = _box(client, h, center_id, destination="Mérida")
        token = pkg["tracking"]["tracking_token"]

        option = client.get(f"{TRACK}/{token}", headers=h).json()["packing"]["options"][
            0
        ]
        resp = client.post(
            f"{CENTERS}/{option['collection_center_id']}/shipments/"
            f"{option['shipment_id']}/contents",
            headers=h,
            json={"tracking_token": token},
        )
        assert resp.status_code == 201, resp.text

        packing = client.get(f"{TRACK}/{token}", headers=h).json()["packing"]
        assert packing["current_shipment_id"] == box["id"]


class TestBoxManifestOnScan:
    """A scanned box shows what is coming — itemised for staff, counts for all."""

    def test_staff_see_the_itemised_manifest(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        maker = make_user(username="maker1")
        h, admin_h, maker_h = (
            auth_headers(normal_user),
            auth_headers(admin),
            auth_headers(maker),
        )
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        pkg = _package(client, maker_h, center_id, qty=12)
        box = _box(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )

        summary = client.get(f"{TRACK}/{box['tracking_token']}", headers=h).json()[
            "shipment"
        ]
        assert len(summary["entries"]) == 1
        entry = summary["entries"][0]
        assert entry["redacted"] is False
        assert entry["quantity"] == 12
        assert entry["resource_name"] == "Ferula"
        assert entry["maker_username"] == "maker1"
        assert entry["contribution_status"] == "claimed"

    def test_a_guest_gets_counts_but_no_lines(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        maker = make_user(username="maker1")
        h, admin_h, maker_h = (
            auth_headers(normal_user),
            auth_headers(admin),
            auth_headers(maker),
        )
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        # Public visibility on purpose: even a package anyone could open one
        # token at a time is not listed to a stranger holding the carton.
        pkg = _package(client, maker_h, center_id, qty=12)
        box = _box(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=pkg["tracking"]["group_id"],
        )

        guest = client.get(f"{TRACK}/{box['tracking_token']}")
        summary = guest.json()["shipment"]
        # The box still adds up for anyone who scans it...
        assert summary["package_count"] == 1
        assert summary["units_total"] == 12
        # Every package is withheld from a non-custodian, public or not.
        assert summary["hidden_count"] == 1
        # ...but photographing a label must not enumerate who sent what.
        assert summary["entries"] == []
        assert "maker1" not in guest.text

    def test_a_nested_box_is_listed_with_its_load(
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
        pkg = _package(client, h, center_id, qty=5)
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

        summary = client.get(f"{TRACK}/{outer['tracking_token']}", headers=h).json()[
            "shipment"
        ]
        entry = summary["entries"][0]
        assert entry["kind"] == "box"
        assert entry["child_destination"] == "Texas"
        assert entry["child_package_count"] == 1
