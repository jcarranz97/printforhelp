"""Tests for the caller's own cross-center shipment queue (``/shipments/mine``).

The centers tab is the public directory; this is where a center's people
actually work their boxes. Scoped by **roster**, not by who pressed create.
"""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.users.constants import UserRole
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
MINE = "/api/v1/shipments/mine"

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
    date: str = "2026-08-01",
    destination_center_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"shipment_date": date}
    if destination_center_id is not None:
        body["destination_collection_center_id"] = destination_center_id
    resp = client.post(f"{CENTERS}/{center_id}/shipments", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestMyShipments:
    def test_requires_auth(self, client: TestClient):
        assert client.get(MINE).status_code in (401, 403)

    def test_lists_shipments_from_centers_i_own(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h, "UCAB Lab")
        _shipment(client, h, center_id)

        body = client.get(MINE, headers=h).json()
        assert len(body) == 1
        assert body[0]["collection_center_name"] == "UCAB Lab"
        assert body[0]["package_count"] == 0
        assert body[0]["tracking_token"]

    def test_a_contributor_sees_the_centers_queue(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The point of scoping by roster: a helper sees the same boxes.

        The owner created this shipment, not the contributor — and the
        contributor must still see it, or a handover would depend on which of
        them happened to press create.
        """
        helper = make_user(username="helper")
        owner_h, helper_h = auth_headers(normal_user), auth_headers(helper)
        center_id = _center(client, owner_h, "UCAB Lab")
        _shipment(client, owner_h, center_id)

        assert client.get(MINE, headers=helper_h).json() == []
        resp = client.post(
            f"{CENTERS}/{center_id}/contributors",
            headers=owner_h,
            json={"username": "helper"},
        )
        assert resp.status_code in (200, 201), resp.text

        body = client.get(MINE, headers=helper_h).json()
        assert len(body) == 1
        assert body[0]["collection_center_name"] == "UCAB Lab"

    def test_a_contributor_can_create_a_shipment(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Roster membership is what authorizes, not the maintainer role."""
        helper = make_user(username="helper")
        owner_h, helper_h = auth_headers(normal_user), auth_headers(helper)
        center_id = _center(client, owner_h, "UCAB Lab")
        client.post(
            f"{CENTERS}/{center_id}/contributors",
            headers=owner_h,
            json={"username": "helper"},
        )

        resp = client.post(
            f"{CENTERS}/{center_id}/shipments",
            headers=helper_h,
            json={"shipment_date": "2026-09-01"},
        )
        assert resp.status_code == 201, resp.text

    def test_other_peoples_centers_are_not_listed(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user(username="stranger")
        h = auth_headers(normal_user)
        center_id = _center(client, h, "UCAB Lab")
        _shipment(client, h, center_id)

        assert client.get(MINE, headers=auth_headers(stranger)).json() == []

    def test_relay_destination_name_is_resolved(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Named even though the caller does not staff the destination."""
        relay_owner = make_user(username="relay")
        h, relay_h = auth_headers(normal_user), auth_headers(relay_owner)
        origin_id = _center(client, h, "California")
        relay_id = _center(client, relay_h, "Texas")
        _shipment(client, h, origin_id, destination_center_id=relay_id)

        body = client.get(MINE, headers=h).json()
        assert body[0]["destination_collection_center_name"] == "Texas"

    def test_newest_first_across_centers(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        first = _center(client, h, "Centro A")
        second = _center(client, h, "Centro B")
        _shipment(client, h, first, date="2026-07-01")
        _shipment(client, h, second, date="2026-09-01")

        dates = [s["shipment_date"] for s in client.get(MINE, headers=h).json()]
        assert dates == ["2026-09-01", "2026-07-01"]

    def test_deleted_shipments_drop_out(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        center_id = _center(client, h, "UCAB Lab")
        shipment = _shipment(client, h, center_id)
        client.delete(f"{CENTERS}/{center_id}/shipments/{shipment['id']}", headers=h)
        assert client.get(MINE, headers=h).json() == []

    def test_maintainers_see_only_their_own_centers(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """This is a personal working queue, not the global override view.

        A maintainer *may* act on any center, but listing every shipment on the
        platform here would bury the ones they actually run.
        """
        admin = make_user(username="admin1", role=UserRole.ADMIN)
        h, admin_h = auth_headers(normal_user), auth_headers(admin)
        center_id = _center(client, h, "UCAB Lab")
        _shipment(client, h, center_id)

        assert client.get(MINE, headers=admin_h).json() == []


class TestMyCenters:
    def test_contributed_centers_are_included(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        helper = make_user(username="helper")
        owner_h, helper_h = auth_headers(normal_user), auth_headers(helper)
        center_id = _center(client, owner_h, "UCAB Lab")

        assert client.get(f"{CENTERS}/mine", headers=helper_h).json() == []
        client.post(
            f"{CENTERS}/{center_id}/contributors",
            headers=owner_h,
            json={"username": "helper"},
        )
        mine = client.get(f"{CENTERS}/mine", headers=helper_h).json()
        assert [c["id"] for c in mine] == [center_id]
