"""Tests for the public activity feed and comments (Phase 3, FR-133..135)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.constants import UserRole
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
COMMENTS = "/api/v1/comments"
ACTIVITY = "/api/v1/activity"

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


def _create_shipment(
    client: TestClient, center_id: object, headers: dict[str, str]
) -> dict[str, object]:
    resp = client.post(
        f"{CENTERS}/{center_id}/shipments",
        headers=headers,
        json={"shipment_date": "2026-07-15", "status": "receiving"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_resource(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    resp = client.post(
        RESOURCES,
        headers=headers,
        json={"name": "Ferula", "source_url": "https://example.com/p.stl"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_request(
    client: TestClient, resource_id: object, headers: dict[str, str]
) -> dict[str, object]:
    resp = client.post(
        REQUESTS,
        headers=headers,
        json={
            "title": "Ferulas for Venezuela",
            "items": [{"resource_id": str(resource_id), "quantity": 10}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _post_comment(
    client: TestClient,
    headers: dict[str, str],
    entity_type: str,
    entity_id: object,
    body: str = "Hello **world**",
) -> dict[str, object]:
    resp = client.post(
        COMMENTS,
        headers=headers,
        json={"entity_type": entity_type, "entity_id": str(entity_id), "body": body},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestComments:
    def test_logged_in_user_can_comment_on_center(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        # Markdown is stored verbatim (rendered client-side).
        assert comment["body"] == "Hello **world**"
        author = comment["author"]
        assert isinstance(author, dict)
        assert author["username"] == "user1"

    def test_comment_on_shipment(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "shipment", shipment["id"]
        )
        assert comment["entity_type"] == "shipment"

    def test_comment_on_resource(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "resource", resource["id"]
        )
        assert comment["entity_type"] == "resource"

    def test_comment_on_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        request = _create_request(client, resource["id"], auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "request", request["id"]
        )
        assert comment["entity_type"] == "request"

    def test_anonymous_cannot_comment(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            COMMENTS,
            json={
                "entity_type": "collection_center",
                "entity_id": center["id"],
                "body": "hi",
            },
        )
        assert resp.status_code == 401

    def test_blank_body_is_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            COMMENTS,
            headers=auth_headers(normal_user),
            json={
                "entity_type": "collection_center",
                "entity_id": center["id"],
                "body": "   ",
            },
        )
        assert resp.status_code == 422

    def test_comment_on_missing_entity_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            COMMENTS,
            headers=auth_headers(normal_user),
            json={
                "entity_type": "collection_center",
                "entity_id": str(uuid.uuid4()),
                "body": "hi",
            },
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "INVALID_ENTITY_REFERENCE"

    def test_comment_on_tracking_group_is_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        # Tracking groups are watchable but not commentable: the guard fires
        # before any existence check, so even a real group id is rejected.
        resp = client.post(
            COMMENTS,
            headers=auth_headers(normal_user),
            json={
                "entity_type": "tracking_group",
                "entity_id": str(uuid.uuid4()),
                "body": "hi",
            },
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "INVALID_ENTITY_REFERENCE"

    def test_public_list_visible_without_auth(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        resp = client.get(
            COMMENTS,
            params={"entity_type": "collection_center", "entity_id": center["id"]},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_author_can_edit(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        resp = client.patch(
            f"{COMMENTS}/{comment['id']}",
            headers=auth_headers(normal_user),
            json={"body": "Edited"},
        )
        assert resp.status_code == 200
        assert resp.json()["body"] == "Edited"
        assert resp.json()["edited_at"] is not None

    def test_non_author_cannot_edit(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        other = make_user("other")
        resp = client.patch(
            f"{COMMENTS}/{comment['id']}",
            headers=auth_headers(other),
            json={"body": "Hijack"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "COMMENT_NOT_AUTHOR"

    def test_author_can_delete(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        resp = client.delete(
            f"{COMMENTS}/{comment['id']}", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 204
        listed = client.get(
            COMMENTS,
            params={"entity_type": "collection_center", "entity_id": center["id"]},
        ).json()
        assert listed == []

    def test_admin_can_delete_others_comment(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        resp = client.delete(
            f"{COMMENTS}/{comment['id']}", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 204

    def test_non_author_non_admin_cannot_delete(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        comment = _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        other = make_user("other")
        resp = client.delete(f"{COMMENTS}/{comment['id']}", headers=auth_headers(other))
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "COMMENT_DELETE_FORBIDDEN"

    def test_edit_missing_comment_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.patch(
            f"{COMMENTS}/{uuid.uuid4()}",
            headers=auth_headers(normal_user),
            json={"body": "x"},
        )
        assert resp.status_code == 404


class TestActivityFeed:
    def test_shipment_lifecycle_recorded(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        client.patch(
            f"{CENTERS}/{center['id']}/shipments/{shipment['id']}",
            headers=auth_headers(normal_user),
            json={"status": "closed"},
        )
        resp = client.get(
            ACTIVITY,
            params={"entity_type": "shipment", "entity_id": shipment["id"]},
        )
        assert resp.status_code == 200
        actions = [e["action"] for e in resp.json()]
        # Newest first: status_changed then created.
        assert actions == ["status_changed", "created"]
        status_change = resp.json()[0]["changes"]["status"]
        assert status_change == {"from": "receiving", "to": "closed"}

    def test_comment_appears_in_activity(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        center = _create_center(client, auth_headers(normal_user))
        _post_comment(
            client, auth_headers(normal_user), "collection_center", center["id"]
        )
        resp = client.get(
            ACTIVITY,
            params={"entity_type": "collection_center", "entity_id": center["id"]},
        )
        assert resp.status_code == 200
        assert resp.json()[0]["action"] == "commented"

    def test_maintainer_status_change_uses_override(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        center = _create_center(client, auth_headers(normal_user))
        shipment = _create_shipment(client, center["id"], auth_headers(normal_user))
        maintainer = make_user("maint", UserRole.MAINTAINER)
        resp = client.patch(
            f"{CENTERS}/{center['id']}/shipments/{shipment['id']}",
            headers=auth_headers(maintainer),
            json={"status": "cancelled"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"
