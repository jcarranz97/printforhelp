"""Tests for Request + RequestItem endpoints (Phase 4)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User

PARTS = "/api/v1/parts"
REQUESTS = "/api/v1/requests"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _create_part(
    client: TestClient, headers: dict[str, str], name: str = "Ferula"
) -> str:
    resp = client.post(
        PARTS,
        headers=headers,
        json={"name": name, "source_url": "https://example.com/p.stl"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_request(
    client: TestClient, headers: dict[str, str], part_id: str, quantity: int | None = 10
) -> dict[str, object]:
    item: dict[str, object] = {"part_id": part_id}
    if quantity is not None:
        item["quantity"] = quantity
    resp = client.post(
        REQUESTS,
        headers=headers,
        json={"title": "Ferulas for Venezuela", "items": [item]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateRequest:
    def test_requires_auth(self, client: TestClient):
        assert client.post(REQUESTS, json={}).status_code == 401

    def test_requires_at_least_one_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            REQUESTS,
            headers=auth_headers(normal_user),
            json={"title": "x", "items": []},
        )
        assert resp.status_code == 422

    def test_rejects_discontinued_part(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        client.post(f"{PARTS}/{part_id}/discontinue", headers=h)
        resp = client.post(
            REQUESTS,
            headers=h,
            json={"title": "x", "items": [{"part_id": part_id}]},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PART_DISCONTINUED"

    def test_creates_with_requester_and_progress(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id, quantity=10)
        assert request["requester_user_id"] == str(normal_user.id)
        assert request["status"] == "open"
        item = request["items"][0]
        assert item["progress"] == {
            "target_quantity": 10,
            "claimed_quantity": 0,
            "at_center_quantity": 0,
            "committed_quantity": 0,
            "remaining": 10,
        }

    def test_null_quantity_has_null_remaining(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id, quantity=None)
        assert request["items"][0]["progress"]["remaining"] is None


class TestListAndGet:
    def test_list_defaults_to_open(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        assert request["id"] in {r["id"] for r in client.get(REQUESTS).json()}
        client.post(f"{REQUESTS}/{request['id']}/close", headers=h, json={})
        assert request["id"] not in {r["id"] for r in client.get(REQUESTS).json()}
        closed = client.get(REQUESTS, params={"status": "closed"}).json()
        assert request["id"] in {r["id"] for r in closed}

    def test_get_unknown_is_404(self, client: TestClient):
        assert client.get(f"{REQUESTS}/{uuid.uuid4()}").status_code == 404


class TestEditAndClose:
    def test_only_requester_can_edit(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        other = make_user("stranger")
        resp = client.put(
            f"{REQUESTS}/{request['id']}",
            headers=auth_headers(other),
            json={"title": "Nope"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_REQUESTER"

    def test_edit_then_close(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        edited = client.put(
            f"{REQUESTS}/{request['id']}", headers=h, json={"title": "Updated"}
        ).json()
        assert edited["title"] == "Updated"
        closed = client.post(
            f"{REQUESTS}/{request['id']}/close", headers=h, json={"reason": "done"}
        ).json()
        assert closed["status"] == "closed"
        assert closed["closed_reason"] == "done"
        assert closed["items"][0]["status"] == "closed"

    def test_cannot_edit_closed_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        client.post(f"{REQUESTS}/{request['id']}/close", headers=h, json={})
        resp = client.put(f"{REQUESTS}/{request['id']}", headers=h, json={"title": "x"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NOT_OPEN"


class TestItems:
    def test_add_and_close_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        part2 = _create_part(client, h, name="Ferula 2")
        item = client.post(
            f"{REQUESTS}/{request['id']}/items",
            headers=h,
            json={"part_id": part2, "quantity": 5},
        ).json()
        assert item["status"] == "open"
        closed = client.post(
            f"{REQUESTS}/{request['id']}/items/{item['id']}/close",
            headers=h,
            json={},
        ).json()
        assert closed["status"] == "closed"
        assert closed["closed_reason"] == "request_item_closed"

    def test_cannot_remove_last_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        item_id = request["items"][0]["id"]
        resp = client.delete(f"{REQUESTS}/{request['id']}/items/{item_id}", headers=h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NEEDS_ITEM"

    def test_remove_extra_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        part2 = _create_part(client, h, name="Ferula 2")
        item = client.post(
            f"{REQUESTS}/{request['id']}/items",
            headers=h,
            json={"part_id": part2},
        ).json()
        resp = client.delete(
            f"{REQUESTS}/{request['id']}/items/{item['id']}", headers=h
        )
        assert resp.status_code == 204
        detail = client.get(f"{REQUESTS}/{request['id']}").json()
        assert len(detail["items"]) == 1

    def test_item_request_mismatch_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part_id = _create_part(client, h)
        request = _create_request(client, h, part_id)
        resp = client.post(
            f"{REQUESTS}/{request['id']}/items/{uuid.uuid4()}/close",
            headers=h,
            json={},
        )
        assert resp.status_code == 404
