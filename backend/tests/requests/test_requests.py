"""Tests for Request + RequestItem endpoints (Phase 4)."""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.users.models import User

RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CENTERS = "/api/v1/collection-centers"
CONTRIB = "/api/v1/contributions"
COMMENTS = "/api/v1/comments"
ACTIVITY = "/api/v1/activity"
WATCHES = "/api/v1/watches"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _verified_center(
    client: TestClient,
    owner_h: dict[str, str],
    admin_h: dict[str, str],
    name: str = "Centro",
) -> str:
    cc = client.post(
        CENTERS,
        headers=owner_h,
        json={
            "name": name,
            "address": "Av. 1",
            "country": "VE",
            "city": "Caracas",
            "contact": "x@y.z",
        },
    ).json()
    client.post(f"{CENTERS}/{cc['id']}/verify", headers=admin_h)
    return cc["id"]


def _create_resource(
    client: TestClient, headers: dict[str, str], name: str = "Ferula"
) -> str:
    resp = client.post(
        RESOURCES,
        headers=headers,
        json={"name": name, "source_url": "https://example.com/p.stl"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# Returns the parsed JSON response body (a dynamic shape), so the value
# type is Any to let tests index nested fields (items, progress) without
# casts.
def _create_request(
    client: TestClient,
    headers: dict[str, str],
    resource_id: str,
    quantity: int | None = 10,
) -> dict[str, Any]:
    item: dict[str, object] = {"resource_id": resource_id}
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

    def test_creates_without_items(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        # Items are optional (FR-038): a request may start empty and have
        # resources added later.
        resp = client.post(
            REQUESTS,
            headers=auth_headers(normal_user),
            json={"title": "x", "items": []},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["items"] == []
        assert resp.json()["status"] == "open"

    def test_creates_with_items_omitted(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            REQUESTS,
            headers=auth_headers(normal_user),
            json={"title": "x"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["items"] == []

    def test_rejects_discontinued_resource(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        client.post(f"{RESOURCES}/{resource_id}/discontinue", headers=h)
        resp = client.post(
            REQUESTS,
            headers=h,
            json={"title": "x", "items": [{"resource_id": resource_id}]},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_DISCONTINUED"

    def test_creates_with_requester_and_progress(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=10)
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
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=None)
        assert request["items"][0]["progress"]["remaining"] is None

    def test_stores_image_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        resp = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "x",
                "image_url": "https://cdn.example.com/cover.png",
                "items": [{"resource_id": resource_id}],
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["image_url"] == "https://cdn.example.com/cover.png"

    def test_accepts_relative_media_image_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        # Our own uploads return a site-relative /media path when
        # MEDIA_BASE_URL is unset; the schema must accept it.
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        resp = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "x",
                "image_url": "/media/images/x.png",
                "items": [{"resource_id": resource_id}],
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["image_url"] == "/media/images/x.png"

    def test_rejects_protocol_relative_image_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        # A "//host" value points at an external origin and must be rejected.
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        resp = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "x",
                "image_url": "//evil.example.com/x.png",
                "items": [{"resource_id": resource_id}],
            },
        )
        assert resp.status_code == 422

    def test_update_changes_image_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        resp = client.put(
            f"{REQUESTS}/{request['id']}",
            headers=h,
            json={"image_url": "https://cdn.example.com/new.png"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["image_url"] == "https://cdn.example.com/new.png"


class TestListAndGet:
    def test_list_defaults_to_open(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        assert request["id"] in {r["id"] for r in client.get(REQUESTS).json()}
        client.post(f"{REQUESTS}/{request['id']}/close", headers=h, json={})
        assert request["id"] not in {r["id"] for r in client.get(REQUESTS).json()}
        closed = client.get(REQUESTS, params={"status": "closed"}).json()
        assert request["id"] in {r["id"] for r in closed}

    def test_get_unknown_is_404(self, client: TestClient):
        assert client.get(f"{REQUESTS}/{uuid.uuid4()}").status_code == 404

    def test_list_reports_effective_center_countries(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        ah = auth_headers(admin_user)
        center = _verified_center(client, h, ah, name="Caracas")
        resource_id = _create_resource(client, h)
        request = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "Ferulas",
                "preferred_collection_center_ids": [center],
                "items": [{"resource_id": resource_id}],
            },
        ).json()
        row = next(r for r in client.get(REQUESTS).json() if r["id"] == request["id"])
        # Single VE drop-off -> the directory can render an "Only Venezuela" flag.
        assert row["countries"] == ["VE"]

    def test_list_countries_empty_without_centers(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        row = next(r for r in client.get(REQUESTS).json() if r["id"] == request["id"])
        assert row["countries"] == []


class TestEditAndClose:
    def test_only_requester_can_edit(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
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
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
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
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        client.post(f"{REQUESTS}/{request['id']}/close", headers=h, json={})
        resp = client.put(f"{REQUESTS}/{request['id']}", headers=h, json={"title": "x"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NOT_OPEN"

    def test_reopen_closed_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        rid = request["id"]

        client.post(f"{REQUESTS}/{rid}/close", headers=h, json={})
        closed = client.get(f"{REQUESTS}/{rid}").json()
        assert closed["status"] == "closed"
        assert closed["items"][0]["status"] == "closed"

        # Reopening restores the campaign and the items it closed on the way.
        reopened = client.post(f"{REQUESTS}/{rid}/reopen", headers=h)
        assert reopened.status_code == 200, reopened.text
        body = reopened.json()
        assert body["status"] == "open"
        assert body["items"][0]["status"] == "open"

        # Reopening an already-open request is rejected.
        again = client.post(f"{REQUESTS}/{rid}/reopen", headers=h)
        assert again.status_code == 409
        assert again.json()["error"]["code"] == "REQUEST_NOT_CLOSED"


class TestItems:
    def test_item_unit_set_on_create_and_editable(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        # A supply carrying suggested units.
        supply = client.post(
            RESOURCES,
            headers=h,
            json={"name": "Agua", "category": "other", "units": ["litros"]},
        ).json()["id"]
        request = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "Agua para Caracas",
                "items": [{"resource_id": supply, "quantity": 5, "unit": "  litros  "}],
            },
        ).json()
        item = request["items"][0]
        # The chosen unit is trimmed and returned on the item.
        assert item["unit"] == "litros"

        # A field requester can change the unit later.
        updated = client.patch(
            f"{REQUESTS}/{request['id']}/items/{item['id']}",
            headers=h,
            json={"unit": "cubetas"},
        ).json()
        assert updated["unit"] == "cubetas"

    def test_item_preferred_centers_subset(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        ah = auth_headers(admin_user)
        c1 = _verified_center(client, h, ah, name="C1")
        c2 = _verified_center(client, h, ah, name="C2")
        other = _verified_center(client, h, ah, name="C3")
        resource_id = _create_resource(client, h)
        # Request prefers two centers; the item narrows to one of them.
        request = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "R",
                "preferred_collection_center_ids": [c1, c2],
                "items": [
                    {
                        "resource_id": resource_id,
                        "preferred_collection_center_ids": [c1],
                    }
                ],
            },
        ).json()
        item = request["items"][0]
        assert item["preferred_collection_center_ids"] == [c1]

        # Updating narrows to c2; a center not preferred by the request is
        # dropped (the item subset stays within the request's list).
        updated = client.patch(
            f"{REQUESTS}/{request['id']}/items/{item['id']}",
            headers=h,
            json={"preferred_collection_center_ids": [c2, other]},
        ).json()
        assert updated["preferred_collection_center_ids"] == [c2]

    def test_item_countries_reflect_effective_centers(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        ah = auth_headers(admin_user)
        ve = _verified_center(client, h, ah, name="Caracas")
        # A second verified center in a different country.
        mx = client.post(
            CENTERS,
            headers=h,
            json={
                "name": "CDMX",
                "address": "Av. 2",
                "country": "Mexico",
                "city": "Mexico City",
                "contact": "a@b.c",
            },
        ).json()["id"]
        client.post(f"{CENTERS}/{mx}/verify", headers=ah)
        resource_id = _create_resource(client, h)
        # Request prefers both countries; item 1 narrows to the Mexico center,
        # item 2 leaves it open (so it inherits both).
        request = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "R",
                "preferred_collection_center_ids": [ve, mx],
                "items": [
                    {
                        "resource_id": resource_id,
                        "preferred_collection_center_ids": [mx],
                    },
                    {"resource_id": _create_resource(client, h, name="Ferula 2")},
                ],
            },
        ).json()
        by_number = {i["item_number"]: i for i in request["items"]}
        # The narrowed item sees only Mexico; the open item inherits both.
        assert by_number[1]["countries"] == ["Mexico"]
        assert by_number[2]["countries"] == ["Mexico", "VE"]

    def test_reopen_closed_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        rid = request["id"]
        second = _create_resource(client, h, name="Ferula 2")
        item = client.post(
            f"{REQUESTS}/{rid}/items",
            headers=h,
            json={"resource_id": second},
        ).json()
        client.post(f"{REQUESTS}/{rid}/items/{item['id']}/close", headers=h, json={})

        reopened = client.post(f"{REQUESTS}/{rid}/items/{item['id']}/reopen", headers=h)
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()["status"] == "open"

        # Reopening an already-open item is rejected.
        again = client.post(f"{REQUESTS}/{rid}/items/{item['id']}/reopen", headers=h)
        assert again.status_code == 409
        assert again.json()["error"]["code"] == "REQUEST_ITEM_NOT_CLOSED"

    def test_add_and_close_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        resource2 = _create_resource(client, h, name="Ferula 2")
        item = client.post(
            f"{REQUESTS}/{request['id']}/items",
            headers=h,
            json={"resource_id": resource2, "quantity": 5},
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
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        item_id = request["items"][0]["id"]
        resp = client.delete(f"{REQUESTS}/{request['id']}/items/{item_id}", headers=h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NEEDS_ITEM"

    def test_remove_extra_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        resource2 = _create_resource(client, h, name="Ferula 2")
        item = client.post(
            f"{REQUESTS}/{request['id']}/items",
            headers=h,
            json={"resource_id": resource2},
        ).json()
        resp = client.delete(
            f"{REQUESTS}/{request['id']}/items/{item['id']}", headers=h
        )
        assert resp.status_code == 204
        detail = client.get(f"{REQUESTS}/{request['id']}").json()
        assert len(detail["items"]) == 1

    def test_update_item_target(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=10)
        item_id = request["items"][0]["id"]
        resp = client.patch(
            f"{REQUESTS}/{request['id']}/items/{item_id}",
            headers=h,
            json={"quantity": 25},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["quantity"] == 25
        assert body["progress"]["target_quantity"] == 25
        assert body["progress"]["remaining"] == 25

    def test_update_item_requires_requester(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        item_id = request["items"][0]["id"]
        other = make_user("stranger2")
        resp = client.patch(
            f"{REQUESTS}/{request['id']}/items/{item_id}",
            headers=auth_headers(other),
            json={"quantity": 5},
        )
        assert resp.status_code == 403

    def test_create_allows_duplicate_resources(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        # A need for the same part can recur, so duplicates are allowed and
        # each becomes its own independently-tracked item.
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        resp = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "Dup",
                "items": [{"resource_id": resource_id}, {"resource_id": resource_id}],
            },
        )
        assert resp.status_code == 201, resp.text
        items = resp.json()["items"]
        assert len(items) == 2
        assert {i["resource_id"] for i in items} == {resource_id}
        assert items[0]["id"] != items[1]["id"]

    def test_add_allows_duplicate_resource(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        resp = client.post(
            f"{REQUESTS}/{request['id']}/items",
            headers=h,
            json={"resource_id": resource_id, "quantity": 3},
        )
        assert resp.status_code == 201, resp.text
        detail = client.get(f"{REQUESTS}/{request['id']}").json()
        assert len(detail["items"]) == 2

    def test_item_request_mismatch_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        resp = client.post(
            f"{REQUESTS}/{request['id']}/items/{uuid.uuid4()}/close",
            headers=h,
            json={},
        )
        assert resp.status_code == 404


class TestItemNumbering:
    def test_items_numbered_from_one_per_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        # Two duplicate items on create, then a third added later.
        request = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "Numbered",
                "items": [{"resource_id": resource_id}, {"resource_id": resource_id}],
            },
        ).json()
        assert [i["item_number"] for i in request["items"]] == [1, 2]
        added = client.post(
            f"{REQUESTS}/{request['id']}/items",
            headers=h,
            json={"resource_id": resource_id},
        )
        assert added.json()["item_number"] == 3

    def test_numbers_are_scoped_per_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_a = _create_resource(client, h, name="A")
        resource_b = _create_resource(client, h, name="B")
        request_a = _create_request(client, h, resource_a)
        request_b = _create_request(client, h, resource_b)
        # Both have an item #1, but they resolve to their own resource.
        detail_a = client.get(f"{REQUESTS}/{request_a['id']}/items/1").json()
        detail_b = client.get(f"{REQUESTS}/{request_b['id']}/items/1").json()
        assert detail_a["resource_name"] == "A"
        assert detail_b["resource_name"] == "B"


class TestItemDetail:
    def test_item_detail_is_public(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=10)
        number = request["items"][0]["item_number"]
        # No auth header: the shareable page is public.
        resp = client.get(f"{REQUESTS}/{request['id']}/items/{number}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["item_number"] == number
        assert body["resource_name"] == "Ferula"
        assert body["request_title"] == "Ferulas for Venezuela"
        assert body["request_status"] == "open"
        assert body["progress"]["target_quantity"] == 10
        assert body["last_activity_at"] is not None

    def test_item_detail_unknown_number_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        resp = client.get(f"{REQUESTS}/{request['id']}/items/999")
        assert resp.status_code == 404

    def test_item_detail_unknown_request_is_404(self, client: TestClient):
        resp = client.get(f"{REQUESTS}/{uuid.uuid4()}/items/1")
        assert resp.status_code == 404


class TestItemCommitments:
    def test_lists_commitments_and_omits_private_fields(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        ah = auth_headers(admin_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=10)
        item = request["items"][0]
        center_id = _verified_center(client, h, ah)
        claim = client.post(
            CONTRIB,
            headers=h,
            json={
                # The claim still addresses the item by its UUID.
                "request_item_id": item["id"],
                "collection_center_id": center_id,
                "quantity": 4,
            },
        )
        assert claim.status_code == 201, claim.text

        # Public read, addressed by the short item number, no auth header.
        resp = client.get(
            f"{REQUESTS}/{request['id']}/items/{item['item_number']}/contributions"
        )
        assert resp.status_code == 200, resp.text
        rows = resp.json()
        assert len(rows) == 1
        row = rows[0]
        assert row["maker_username"] == normal_user.username
        assert row["quantity"] == 4
        assert row["status"] == "claimed"
        assert row["collection_center_name"] == "Centro"
        # The maker's private fields never leak to the public list.
        assert "notes" not in row
        assert "tags" not in row

    def test_commitments_scoped_per_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        other = _create_request(client, h, resource_id)
        client.post(
            CONTRIB,
            headers=h,
            json={"request_item_id": request["items"][0]["id"], "quantity": 2},
        )
        # `other` has its own item #1 with no commitments.
        resp = client.get(f"{REQUESTS}/{other['id']}/items/1/contributions")
        assert resp.status_code == 200
        assert resp.json() == []
        mine = client.get(f"{REQUESTS}/{request['id']}/items/1/contributions")
        assert len(mine.json()) == 1


class TestItemActivityAndComments:
    def test_claim_records_item_activity(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=10)
        item_id = request["items"][0]["id"]
        client.post(
            CONTRIB, headers=h, json={"request_item_id": item_id, "quantity": 2}
        )
        entries = client.get(
            ACTIVITY,
            params={"entity_type": "request_item", "entity_id": item_id},
        ).json()
        assert any(e["action"] == "created" for e in entries)

    def test_comment_on_request_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id)
        item_id = request["items"][0]["id"]
        posted = client.post(
            COMMENTS,
            headers=h,
            json={"entity_type": "request_item", "entity_id": item_id, "body": "hola"},
        )
        assert posted.status_code == 201, posted.text
        listed = client.get(
            COMMENTS,
            params={"entity_type": "request_item", "entity_id": item_id},
        ).json()
        assert any(c["body"] == "hola" for c in listed)

    def test_status_change_notifies_item_watcher(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maker_h = auth_headers(normal_user)
        watcher = make_user("watcher")
        watcher_h = auth_headers(watcher)
        resource_id = _create_resource(client, maker_h)
        request = _create_request(client, maker_h, resource_id, quantity=10)
        item = request["items"][0]
        item_id = item["id"]
        # A second user watches the item.
        client.post(
            WATCHES,
            headers=watcher_h,
            json={"entity_type": "request_item", "entity_id": item_id},
        )
        contribution = client.post(
            CONTRIB, headers=maker_h, json={"request_item_id": item_id, "quantity": 2}
        ).json()
        client.post(f"{CONTRIB}/{contribution['id']}/mark-prepared", headers=maker_h)
        notes = client.get("/api/v1/notifications", headers=watcher_h).json()
        # The notification deep-links using the short item number, not the UUID.
        link = f"/requests/{request['id']}/items/{item['item_number']}"
        assert any(link in n["link"] for n in notes)


class TestHelpState:
    def test_needs_help_by_default(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=10)
        row = next(r for r in client.get(REQUESTS).json() if r["id"] == request["id"])
        assert row["help_state"] == "needs_help"
        assert row["last_activity_at"] is not None

    def test_committed_when_enough_claimed(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=5)
        item_id = request["items"][0]["id"]
        # Enough claimed (no center needed) so no more help is needed.
        client.post(
            CONTRIB, headers=h, json={"request_item_id": item_id, "quantity": 5}
        )
        row = next(r for r in client.get(REQUESTS).json() if r["id"] == request["id"])
        assert row["help_state"] == "committed"

    def test_completed_when_received(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        ah = auth_headers(admin_user)
        resource_id = _create_resource(client, h)
        request = _create_request(client, h, resource_id, quantity=3)
        item_id = request["items"][0]["id"]
        # The maker owns the center, so delivery auto-receives (FR-126) and
        # the item/campaign auto-fulfill.
        center_id = _verified_center(client, h, ah)
        contribution = client.post(
            CONTRIB,
            headers=h,
            json={
                "request_item_id": item_id,
                "collection_center_id": center_id,
                "quantity": 3,
            },
        ).json()
        client.post(f"{CONTRIB}/{contribution['id']}/mark-prepared", headers=h)
        client.post(f"{CONTRIB}/{contribution['id']}/mark-delivered", headers=h)
        row = next(r for r in client.get(REQUESTS).json() if r["id"] == request["id"])
        assert row["status"] == "fulfilled"
        assert row["help_state"] == "completed"
