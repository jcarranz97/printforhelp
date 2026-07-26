"""Tests for packing shipments: the containment graph and manifest redaction.

Covers FR-138 (contents), FR-139 (one active parent), FR-140 (no cycles, depth
cap), FR-146 (manifest redaction) and FR-147 (unpacking is a soft delete).
"""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.shipments.constants import MAX_SHIPMENT_DEPTH
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
    resp = client.post(
        CENTERS,
        headers=headers,
        json={
            "name": name,
            "address": "Av. 1",
            "country": "VE",
            "city": "Caracas",
            "contact": "x@y.z",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _shipment(
    client: TestClient,
    headers: dict[str, str],
    center_id: str,
    *,
    destination_center_id: str | None = None,
    status: str = "receiving",
) -> dict[str, Any]:
    body: dict[str, Any] = {"shipment_date": "2026-08-01", "status": status}
    if destination_center_id is not None:
        body["destination_collection_center_id"] = destination_center_id
    resp = client.post(f"{CENTERS}/{center_id}/shipments", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _tracked_package(
    client: TestClient,
    maker_h: dict[str, str],
    admin_h: dict[str, str],
    center_id: str,
    *,
    qty: int = 3,
    visibility: str | None = None,
) -> dict[str, Any]:
    """Create a Contribution into ``center_id`` and generate its tracking QRs."""
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
            "items": [{"resource_id": resource_id, "quantity": 100}],
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
    group = client.post(
        f"{TRACKING}/contributions/{contribution['id']}", headers=maker_h
    ).json()
    if visibility is not None:
        resp = client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=maker_h,
            json={"visibility": visibility},
        )
        assert resp.status_code == 200, resp.text
    return {"contribution": contribution, "tracking": group}


def _contents_url(center_id: str, shipment_id: str) -> str:
    return f"{CENTERS}/{center_id}/shipments/{shipment_id}/contents"


class TestPackPackages:
    def test_pack_by_group_id_and_read_the_manifest(
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
        packed = _tracked_package(client, h, admin_h, center_id, qty=7)
        box = _shipment(client, h, center_id)

        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_group_id": packed["tracking"]["group_id"]},
        )
        assert resp.status_code == 201, resp.text

        manifest = client.get(_contents_url(center_id, box["id"]), headers=h).json()
        assert manifest["contents_total"] == 1
        assert manifest["package_count"] == 1
        assert manifest["units_total"] == 7
        assert manifest["hidden_count"] == 0
        assert manifest["can_manage_contents"] is True
        entry = manifest["entries"][0]
        assert entry["kind"] == "package"
        assert entry["redacted"] is False
        assert entry["resource_name"] == "Ferula"
        assert entry["quantity"] == 7

    def test_pack_by_group_token(
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
        packed = _tracked_package(client, h, admin_h, center_id)
        box = _shipment(client, h, center_id)

        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_token": packed["tracking"]["tracking_token"]},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["tracking_group_id"] == packed["tracking"]["group_id"]

    def test_scanning_one_unit_packs_the_whole_package(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """A staffer scans whatever QR faces them; units belong to a package."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        packed = _tracked_package(client, h, admin_h, center_id, qty=4)
        unit_token = packed["tracking"]["items"][0]["tracking_token"]
        box = _shipment(client, h, center_id)

        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_token": unit_token},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["tracking_group_id"] == packed["tracking"]["group_id"]

    def test_a_pasted_track_url_is_accepted(
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
        packed = _tracked_package(client, h, admin_h, center_id)
        box = _shipment(client, h, center_id)

        token = packed["tracking"]["tracking_token"]
        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_token": f"https://printforhelp.org/track/{token}"},
        )
        assert resp.status_code == 201, resp.text

    def test_unknown_token_is_404(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _shipment(client, h, center_id)
        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_token": "nope-nope-nope"},
        )
        assert resp.status_code == 404

    def test_exactly_one_target_is_required(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _shipment(client, h, center_id)
        url = _contents_url(center_id, box["id"])
        assert client.post(url, headers=h, json={}).status_code == 422
        assert (
            client.post(
                url,
                headers=h,
                json={"tracking_token": "a", "child_shipment_id": box["id"]},
            ).status_code
            == 422
        )

    def test_double_packing_is_rejected(
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
        packed = _tracked_package(client, h, admin_h, center_id)
        first = _shipment(client, h, center_id)
        second = _shipment(client, h, center_id)
        body = {"tracking_group_id": packed["tracking"]["group_id"]}

        assert (
            client.post(
                _contents_url(center_id, first["id"]), headers=h, json=body
            ).status_code
            == 201
        )
        resp = client.post(_contents_url(center_id, second["id"]), headers=h, json=body)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ALREADY_PACKED"

    def test_non_member_cannot_pack(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        stranger = make_user(username="stranger")
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        packed = _tracked_package(client, h, admin_h, center_id)
        box = _shipment(client, h, center_id)

        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=auth_headers(stranger),
            json={"tracking_group_id": packed["tracking"]["group_id"]},
        )
        assert resp.status_code == 403


class TestNesting:
    def test_nest_a_child_box(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        parent = _shipment(client, h, center_id)
        child = _shipment(client, h, center_id)

        resp = client.post(
            _contents_url(center_id, parent["id"]),
            headers=h,
            json={"child_shipment_id": child["id"]},
        )
        assert resp.status_code == 201, resp.text
        manifest = client.get(_contents_url(center_id, parent["id"]), headers=h).json()
        assert manifest["child_count"] == 1
        assert manifest["entries"][0]["kind"] == "box"
        assert manifest["entries"][0]["child_shipment_id"] == child["id"]

    def test_self_nesting_is_rejected(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _shipment(client, h, center_id)
        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"child_shipment_id": box["id"]},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SHIPMENT_CYCLE"

    def test_a_two_step_cycle_is_rejected(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        a = _shipment(client, h, center_id)
        b = _shipment(client, h, center_id)
        assert (
            client.post(
                _contents_url(center_id, a["id"]),
                headers=h,
                json={"child_shipment_id": b["id"]},
            ).status_code
            == 201
        )
        resp = client.post(
            _contents_url(center_id, b["id"]),
            headers=h,
            json={"child_shipment_id": a["id"]},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SHIPMENT_CYCLE"

    def test_depth_cap_is_enforced(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        """Build the deepest legal chain, then prove one more hop is refused."""
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        boxes = [_shipment(client, h, center_id) for _ in range(MAX_SHIPMENT_DEPTH + 1)]
        # Nest boxes[i+1] inside boxes[i] for as long as the cap allows.
        for i in range(MAX_SHIPMENT_DEPTH - 1):
            resp = client.post(
                _contents_url(center_id, boxes[i]["id"]),
                headers=h,
                json={"child_shipment_id": boxes[i + 1]["id"]},
            )
            assert resp.status_code == 201, (i, resp.text)
        resp = client.post(
            _contents_url(center_id, boxes[MAX_SHIPMENT_DEPTH - 1]["id"]),
            headers=h,
            json={"child_shipment_id": boxes[MAX_SHIPMENT_DEPTH]["id"]},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SHIPMENT_TOO_DEEP"

    def test_nested_packages_count_toward_the_parent(
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
        packed = _tracked_package(client, h, admin_h, center_id, qty=5)
        parent = _shipment(client, h, center_id)
        child = _shipment(client, h, center_id)
        client.post(
            _contents_url(center_id, child["id"]),
            headers=h,
            json={"tracking_group_id": packed["tracking"]["group_id"]},
        )
        client.post(
            _contents_url(center_id, parent["id"]),
            headers=h,
            json={"child_shipment_id": child["id"]},
        )

        manifest = client.get(_contents_url(center_id, parent["id"]), headers=h).json()
        # One direct line (the child box), but the package inside it counts.
        assert manifest["contents_total"] == 1
        assert manifest["child_count"] == 1
        assert manifest["package_count"] == 1
        assert manifest["units_total"] == 5
        assert manifest["entries"][0]["child_package_count"] == 1


class TestUnpacking:
    def test_removing_frees_the_package_and_keeps_history(
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
        packed = _tracked_package(client, h, admin_h, center_id)
        first = _shipment(client, h, center_id)
        second = _shipment(client, h, center_id)
        body = {"tracking_group_id": packed["tracking"]["group_id"]}

        content_id = client.post(
            _contents_url(center_id, first["id"]), headers=h, json=body
        ).json()["id"]
        assert (
            client.delete(
                f"{_contents_url(center_id, first['id'])}/{content_id}", headers=h
            ).status_code
            == 204
        )
        manifest = client.get(_contents_url(center_id, first["id"]), headers=h).json()
        assert manifest["contents_total"] == 0

        # Repacking elsewhere is an append, not a move.
        assert (
            client.post(
                _contents_url(center_id, second["id"]), headers=h, json=body
            ).status_code
            == 201
        )

    def test_removing_an_unknown_line_is_404(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h)
        box = _shipment(client, h, center_id)
        missing = "00000000-0000-0000-0000-000000000000"
        resp = client.delete(
            f"{_contents_url(center_id, box['id'])}/{missing}", headers=h
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SHIPMENT_CONTENT_NOT_FOUND"

    def test_deleting_the_box_releases_its_contents(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Otherwise the unique index traps packages inside a dead box."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        packed = _tracked_package(client, h, admin_h, center_id)
        first = _shipment(client, h, center_id)
        second = _shipment(client, h, center_id)
        body = {"tracking_group_id": packed["tracking"]["group_id"]}
        client.post(_contents_url(center_id, first["id"]), headers=h, json=body)

        assert (
            client.delete(
                f"{CENTERS}/{center_id}/shipments/{first['id']}", headers=h
            ).status_code
            == 204
        )
        assert (
            client.post(
                _contents_url(center_id, second["id"]), headers=h, json=body
            ).status_code
            == 201
        )


class TestContentsLock:
    def test_a_dispatched_box_cannot_be_repacked(
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
        packed = _tracked_package(client, h, admin_h, center_id)
        box = _shipment(client, h, center_id, status="in_transit")

        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_group_id": packed["tracking"]["group_id"]},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SHIPMENT_LOCKED"

    def test_an_arrived_box_is_open_again(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """A box sitting open at its destination is where repacking happens."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h)
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        packed = _tracked_package(client, h, admin_h, center_id)
        box = _shipment(client, h, center_id, status="arrived")

        resp = client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_group_id": packed["tracking"]["group_id"]},
        )
        assert resp.status_code == 201, resp.text


class TestManifestRedaction:
    def test_a_guest_sees_counts_but_no_lines(
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
        private = _tracked_package(
            client, h, admin_h, center_id, qty=9, visibility="private"
        )
        box = _shipment(client, h, center_id)
        client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_group_id": private["tracking"]["group_id"]},
        )

        guest = client.get(_contents_url(center_id, box["id"]))
        assert guest.status_code == 200
        body = guest.json()
        # The box's size is on its printed label anyway, so the totals are
        # public; the lines are what a photographed label must not unlock.
        assert body["package_count"] == 1
        assert body["units_total"] == 9
        assert body["hidden_count"] == 1
        assert body["can_manage_contents"] is False
        assert body["entries"] == []
        assert private["tracking"]["tracking_token"] not in guest.text

    def test_a_member_sees_the_whole_manifest(
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
        private = _tracked_package(
            client, h, admin_h, center_id, qty=9, visibility="private"
        )
        box = _shipment(client, h, center_id)
        client.post(
            _contents_url(center_id, box["id"]),
            headers=h,
            json={"tracking_group_id": private["tracking"]["group_id"]},
        )

        body = client.get(_contents_url(center_id, box["id"]), headers=h).json()
        assert body["hidden_count"] == 0
        assert body["units_total"] == 9
        assert body["entries"][0]["redacted"] is False
        assert body["entries"][0]["quantity"] == 9

    def test_destination_center_staff_may_manage_a_relay_box(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Custody, not roster: the receiving hub staffs neither origin nor maker."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        relay_owner = make_user(username="relay")
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        relay_h = auth_headers(relay_owner)

        origin_id = _center(client, h, name="California")
        relay_id = _center(client, relay_h, name="Texas")
        client.post(f"{CENTERS}/{origin_id}/verify", headers=admin_h)
        client.post(f"{CENTERS}/{relay_id}/verify", headers=admin_h)
        box = _shipment(client, h, origin_id, destination_center_id=relay_id)

        body = client.get(_contents_url(origin_id, box["id"]), headers=relay_h).json()
        assert body["can_manage_contents"] is True
