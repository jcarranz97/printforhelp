"""Tests for the shipment lifecycle and bulk receipt on arrival.

Covers FR-141 (status machine), FR-143 (recursive bulk receive with skips),
FR-144 (custody authorizes, not the Contribution's own center) and FR-148
(one update, one notification per person — never one per unit).
"""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.notifications.models import Notification
from app.tracking.models import TrackingRecord
from app.users.constants import UserRole
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CONTRIB = "/api/v1/contributions"
TRACKING = "/api/v1/tracking"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _center(client: TestClient, headers: dict[str, str], name: str) -> str:
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
) -> dict[str, Any]:
    body: dict[str, Any] = {"shipment_date": "2026-08-01"}
    if destination_center_id is not None:
        body["destination_collection_center_id"] = destination_center_id
    resp = client.post(f"{CENTERS}/{center_id}/shipments", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _packed_contribution(
    client: TestClient,
    maker_h: dict[str, str],
    center_id: str,
    *,
    qty: int = 3,
    with_center: bool = True,
) -> dict[str, Any]:
    """Claim a Contribution and generate its tracking group."""
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
            "items": [{"resource_id": resource_id, "quantity": 500}],
        },
    ).json()["items"][0]["id"]
    body: dict[str, Any] = {"request_item_id": item_id, "quantity": qty}
    if with_center:
        body["collection_center_id"] = center_id
    contribution = client.post(CONTRIB, headers=maker_h, json=body).json()
    tracking = client.post(
        f"{TRACKING}/contributions/{contribution['id']}", headers=maker_h
    ).json()
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


class TestStatusMachine:
    def test_dispatch_then_arrive(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h, "Origen")
        box = _shipment(client, h, center_id)
        base = f"{CENTERS}/{center_id}/shipments/{box['id']}"

        dispatched = client.post(f"{base}/dispatch", headers=h)
        assert dispatched.status_code == 200, dispatched.text
        assert dispatched.json()["status"] == "in_transit"
        assert dispatched.json()["dispatched_at"] is not None

        arrived = client.post(f"{base}/arrive", headers=h)
        assert arrived.status_code == 200, arrived.text
        assert arrived.json()["shipment"]["status"] == "arrived"
        assert arrived.json()["shipment"]["arrived_at"] is not None

    def test_arriving_twice_is_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h, "Origen")
        box = _shipment(client, h, center_id)
        base = f"{CENTERS}/{center_id}/shipments/{box['id']}"

        assert client.post(f"{base}/arrive", headers=h).status_code == 200
        second = client.post(f"{base}/arrive", headers=h)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "INVALID_SHIPMENT_TRANSITION"

    def test_illegal_patch_transition_is_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        """A cancelled box is terminal; it cannot quietly go back on the road."""
        h = auth_headers(normal_user)
        center_id = _center(client, h, "Origen")
        box = _shipment(client, h, center_id)
        base = f"{CENTERS}/{center_id}/shipments/{box['id']}"

        assert (
            client.patch(base, headers=h, json={"status": "cancelled"}).status_code
            == 200
        )
        resp = client.patch(base, headers=h, json={"status": "in_transit"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INVALID_SHIPMENT_TRANSITION"

    def test_legacy_receiving_to_closed_still_works(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        """The announcement-style flow the centers already use is untouched."""
        h = auth_headers(normal_user)
        center_id = _center(client, h, "Origen")
        box = _shipment(client, h, center_id)
        resp = client.patch(
            f"{CENTERS}/{center_id}/shipments/{box['id']}",
            headers=h,
            json={"status": "closed"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "closed"

    def test_cancelling_releases_the_contents(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h, "Origen")
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        packed = _packed_contribution(client, h, center_id)
        first = _shipment(client, h, center_id)
        second = _shipment(client, h, center_id)
        group_id = packed["tracking"]["group_id"]
        _pack(client, h, center_id, first["id"], tracking_group_id=group_id)

        client.patch(
            f"{CENTERS}/{center_id}/shipments/{first['id']}",
            headers=h,
            json={"status": "cancelled"},
        )
        # Freed, not trapped in a box that is never leaving.
        _pack(client, h, center_id, second["id"], tracking_group_id=group_id)


class TestBulkReceive:
    def test_arrival_receives_everything_two_levels_down(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        maker = make_user(username="maker1")
        h, admin_h, maker_h = (
            auth_headers(normal_user),
            auth_headers(admin),
            auth_headers(maker),
        )
        center_id = _center(client, h, "Origen")
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)

        inner_pkg = _packed_contribution(client, maker_h, center_id, qty=5)
        outer_pkg = _packed_contribution(client, maker_h, center_id, qty=2)
        inner_box = _shipment(client, h, center_id)
        outer_box = _shipment(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            inner_box["id"],
            tracking_group_id=inner_pkg["tracking"]["group_id"],
        )
        _pack(
            client,
            h,
            center_id,
            outer_box["id"],
            tracking_group_id=outer_pkg["tracking"]["group_id"],
        )
        _pack(client, h, center_id, outer_box["id"], child_shipment_id=inner_box["id"])

        resp = client.post(
            f"{CENTERS}/{center_id}/shipments/{outer_box['id']}/arrive", headers=h
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["packages_total"] == 2
        assert body["received"] == 2
        assert body["skipped_already"] == 0

        for pkg in (inner_pkg, outer_pkg):
            got = client.get(f"{CONTRIB}/me", headers=maker_h).json()
            statuses = {c["id"]: c["status"] for c in got}
            assert statuses[pkg["contribution"]["id"]] == "received"

        # FR-148: exactly one box-level update, not one per package or unit.
        records = (
            db.query(TrackingRecord)
            .filter(TrackingRecord.shipment_id.isnot(None))
            .all()
        )
        assert len(records) == 1

    def test_already_received_packages_are_skipped_not_failed(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The common relay case: the origin center receipted weeks ago."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h, "Origen")
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        # ``normal_user`` owns the center, so delivering auto-receives (FR-126).
        packed = _packed_contribution(client, h, center_id)
        client.post(
            f"{CONTRIB}/{packed['contribution']['id']}/mark-prepared", headers=h
        )
        client.post(
            f"{CONTRIB}/{packed['contribution']['id']}/mark-delivered", headers=h
        )
        box = _shipment(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=packed["tracking"]["group_id"],
        )

        body = client.post(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/arrive", headers=h
        ).json()
        assert body["packages_total"] == 1
        assert body["received"] == 0
        assert body["skipped_already"] == 1

    def test_a_package_without_a_center_is_skipped(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """One odd package must not roll back the rest of the box."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h, "Origen")
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        homeless = _packed_contribution(client, h, center_id, with_center=False)
        normal = _packed_contribution(client, h, center_id, qty=4)
        box = _shipment(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=homeless["tracking"]["group_id"],
        )
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=normal["tracking"]["group_id"],
        )

        body = client.post(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/arrive", headers=h
        ).json()
        assert body["packages_total"] == 2
        assert body["received"] == 1
        assert body["skipped_no_center"] == 1

    def test_receive_contents_is_idempotent(
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
        center_id = _center(client, h, "Origen")
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        packed = _packed_contribution(client, maker_h, center_id)
        box = _shipment(client, h, center_id)
        _pack(
            client,
            h,
            center_id,
            box["id"],
            tracking_group_id=packed["tracking"]["group_id"],
        )
        url = f"{CENTERS}/{center_id}/shipments/{box['id']}/receive-contents"

        first = client.post(url, headers=h).json()
        assert first["received"] == 1
        second = client.post(url, headers=h)
        assert second.status_code == 200
        assert second.json()["received"] == 0
        assert second.json()["skipped_already"] == 1
        # Status is untouched — this is the re-runnable twin of /arrive.
        assert second.json()["shipment"]["status"] == "receiving"

    def test_an_empty_box_arrives_without_drama(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h, "Origen")
        box = _shipment(client, h, center_id)
        body = client.post(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/arrive", headers=h
        ).json()
        assert body["packages_total"] == 0
        assert body["received"] == 0


class TestArrivalAuthorization:
    def test_destination_center_staff_may_sign_for_a_relay_box(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """FR-144: the Texas team staffs neither California nor the maker."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        relay = make_user(username="relay")
        maker = make_user(username="maker1")
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        relay_h, maker_h = auth_headers(relay), auth_headers(maker)

        origin_id = _center(client, h, "California")
        relay_id = _center(client, relay_h, "Texas")
        client.post(f"{CENTERS}/{origin_id}/verify", headers=admin_h)
        client.post(f"{CENTERS}/{relay_id}/verify", headers=admin_h)
        packed = _packed_contribution(client, maker_h, origin_id, qty=6)
        box = _shipment(client, h, origin_id, destination_center_id=relay_id)
        _pack(
            client,
            h,
            origin_id,
            box["id"],
            tracking_group_id=packed["tracking"]["group_id"],
        )

        resp = client.post(
            f"{CENTERS}/{origin_id}/shipments/{box['id']}/arrive", headers=relay_h
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["received"] == 1

    def test_an_unrelated_user_cannot_sign(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user(username="stranger")
        h = auth_headers(normal_user)
        center_id = _center(client, h, "Origen")
        box = _shipment(client, h, center_id)
        resp = client.post(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/arrive",
            headers=auth_headers(stranger),
        )
        assert resp.status_code == 403

    def test_dispatch_requires_custody(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user(username="stranger")
        h = auth_headers(normal_user)
        center_id = _center(client, h, "Origen")
        box = _shipment(client, h, center_id)
        resp = client.post(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/dispatch",
            headers=auth_headers(stranger),
        )
        assert resp.status_code == 403


class TestArrivalNotifications:
    def test_one_notification_per_maker_not_per_package(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        """FR-148. A maker with three packages in one box hears once."""
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        maker = make_user(username="maker1")
        h, admin_h, maker_h = (
            auth_headers(normal_user),
            auth_headers(admin),
            auth_headers(maker),
        )
        center_id = _center(client, h, "Origen")
        client.post(f"{CENTERS}/{center_id}/verify", headers=admin_h)
        box = _shipment(client, h, center_id)
        for _ in range(3):
            packed = _packed_contribution(client, maker_h, center_id, qty=20)
            _pack(
                client,
                h,
                center_id,
                box["id"],
                tracking_group_id=packed["tracking"]["group_id"],
            )

        before = (
            db.query(Notification)
            .filter(Notification.recipient_user_id == maker.id)
            .count()
        )
        resp = client.post(
            f"{CENTERS}/{center_id}/shipments/{box['id']}/arrive", headers=h
        )
        assert resp.json()["received"] == 3
        after = (
            db.query(Notification)
            .filter(Notification.recipient_user_id == maker.id)
            .count()
        )
        # 3 packages x 20 units each; the maker gets exactly one message.
        assert after - before == 1
