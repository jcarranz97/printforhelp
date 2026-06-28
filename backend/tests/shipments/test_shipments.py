"""Tests for the shipments endpoints (Phase 3, FR-130..132)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.constants import UserRole
from app.users.models import User

CENTERS = "/api/v1/collection-centers"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _create_center(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    resp = client.post(
        CENTERS,
        headers=headers,
        json={
            "name": "UCAB Lab - Caracas",
            "address": "Av. Teheran, Caracas",
            "country": "VE",
            "city": "Caracas",
            "contact": "+58-212-407-4400",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _shipments_url(center_id: object) -> str:
    return f"{CENTERS}/{center_id}/shipments"


def _create_shipment(
    client: TestClient,
    center_id: object,
    headers: dict[str, str],
    shipment_date: str = "2026-07-15",
    status: str = "receiving",
) -> dict[str, object]:
    resp = client.post(
        _shipments_url(center_id),
        headers=headers,
        json={
            "shipment_date": shipment_date,
            "status": status,
            "destination": "Caracas, Venezuela",
            "description": "Truck departs at 8am",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateShipment:
    def test_owner_can_create(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        assert shipment["status"] == "receiving"
        assert shipment["destination"] == "Caracas, Venezuela"
        assert shipment["created_by_id"] == str(normal_user.id)

    def test_anonymous_cannot_create(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            _shipments_url(center["id"]),
            json={"shipment_date": "2026-07-15"},
        )
        assert resp.status_code == 401

    def test_non_member_cannot_create(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        stranger = make_user("stranger")
        resp = client.post(
            _shipments_url(center["id"]),
            headers=auth_headers(stranger),
            json={"shipment_date": "2026-07-15"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_MEMBER"

    def test_contributor_can_create(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        helper = make_user("helper")
        add = client.post(
            f"{CENTERS}/{center['id']}/contributors",
            headers=auth_headers(normal_user),
            json={"username": "helper"},
        )
        assert add.status_code == 201, add.text
        shipment = _create_shipment(client, center["id"], auth_headers(helper))
        assert shipment["created_by_id"] == str(helper.id)

    def test_maintainer_can_create_on_any_center(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        maintainer = make_user("maint", UserRole.MAINTAINER)
        shipment = _create_shipment(client, center["id"], auth_headers(maintainer))
        assert shipment["id"]

    def test_create_on_missing_center_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            _shipments_url(uuid.uuid4()),
            headers=auth_headers(normal_user),
            json={"shipment_date": "2026-07-15"},
        )
        assert resp.status_code == 404


class TestReadShipments:
    def test_public_list_is_visible_without_auth(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        _create_shipment(client, center["id"], auth_headers(normal_user))
        resp = client.get(_shipments_url(center["id"]))
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_single_shipment_public(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        resp = client.get(f"{_shipments_url(center['id'])}/{shipment['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == shipment["id"]

    def test_get_missing_shipment_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        resp = client.get(f"{_shipments_url(center['id'])}/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_list_sorted_by_date(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        _create_shipment(
            client, center["id"], auth_headers(normal_user), shipment_date="2026-08-01"
        )
        _create_shipment(
            client, center["id"], auth_headers(normal_user), shipment_date="2026-07-01"
        )
        dates = [
            s["shipment_date"] for s in client.get(_shipments_url(center["id"])).json()
        ]
        assert dates == ["2026-07-01", "2026-08-01"]


class TestUpdateShipment:
    def test_change_status_and_fields(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        resp = client.patch(
            f"{_shipments_url(center['id'])}/{shipment['id']}",
            headers=auth_headers(normal_user),
            json={"status": "closed", "destination": "Maracaibo"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "closed"
        assert resp.json()["destination"] == "Maracaibo"

    def test_update_without_status_change(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        resp = client.patch(
            f"{_shipments_url(center['id'])}/{shipment['id']}",
            headers=auth_headers(normal_user),
            json={"description": "Updated note"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated note"

    def test_non_member_cannot_update(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        stranger = make_user("stranger")
        resp = client.patch(
            f"{_shipments_url(center['id'])}/{shipment['id']}",
            headers=auth_headers(stranger),
            json={"status": "cancelled"},
        )
        assert resp.status_code == 403

    def test_update_missing_shipment_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        resp = client.patch(
            f"{_shipments_url(center['id'])}/{uuid.uuid4()}",
            headers=auth_headers(normal_user),
            json={"status": "closed"},
        )
        assert resp.status_code == 404


class TestDeleteShipment:
    def test_delete_soft_removes(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        resp = client.delete(
            f"{_shipments_url(center['id'])}/{shipment['id']}",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 204
        assert client.get(_shipments_url(center["id"])).json() == []

    def test_non_member_cannot_delete(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        stranger = make_user("stranger")
        resp = client.delete(
            f"{_shipments_url(center['id'])}/{shipment['id']}",
            headers=auth_headers(stranger),
        )
        assert resp.status_code == 403
