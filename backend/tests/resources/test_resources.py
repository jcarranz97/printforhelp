"""Tests for the Resource catalog endpoints (Phase 4)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User

RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _create_resource(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Ferula 1",
    tags: list[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "description": "A wrist splint",
        "source_url": "https://example.com/ferula1.stl",
        "image_url": "https://example.com/ferula1.png",
        "tags": tags if tags is not None else ["ferula", "medical"],
    }
    resp = client.post(RESOURCES, headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateResource:
    def test_requires_auth(self, client: TestClient):
        assert client.post(RESOURCES, json={}).status_code == 401

    def test_invalid_body_is_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(RESOURCES, headers=auth_headers(normal_user), json={})
        assert resp.status_code == 422

    def test_rejects_non_http_source_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            RESOURCES,
            headers=auth_headers(normal_user),
            json={"name": "x", "source_url": "ftp://nope"},
        )
        assert resp.status_code == 422

    def test_owner_defaults_to_caller(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        assert resource["owner_user_id"] == str(normal_user.id)
        assert resource["owner_organization_id"] is None
        assert resource["creator_id"] == str(normal_user.id)
        assert resource["status"] == "active"
        assert resource["image_url"] == "https://example.com/ferula1.png"
        # No label was sent, so it defaults to null.
        assert resource["label_image_url"] is None

    def test_stores_and_updates_label_image_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        created = client.post(
            RESOURCES,
            headers=h,
            json={
                "name": "Ferula",
                "source_url": "https://example.com/f.stl",
                "label_image_url": "https://example.com/label.png",
            },
        )
        assert created.status_code == 201, created.text
        rid = created.json()["id"]
        assert created.json()["label_image_url"] == "https://example.com/label.png"

        updated = client.put(
            f"{RESOURCES}/{rid}",
            headers=h,
            json={"label_image_url": "https://example.com/new-label.png"},
        )
        assert updated.json()["label_image_url"] == "https://example.com/new-label.png"

    def test_rejects_non_http_label_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            RESOURCES,
            headers=auth_headers(normal_user),
            json={
                "name": "x",
                "source_url": "https://example.com/f.stl",
                "label_image_url": "ftp://nope",
            },
        )
        assert resp.status_code == 422


class TestListAndGetResources:
    def test_list_filters_by_tag_and_search(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        _create_resource(client, h, name="Ferula 1", tags=["ferula"])
        _create_resource(client, h, name="Bracket", tags=["other"])
        by_tag = client.get(RESOURCES, params={"tag": "ferula"}).json()
        assert [p["name"] for p in by_tag] == ["Ferula 1"]
        by_search = client.get(RESOURCES, params={"search": "brack"}).json()
        assert [p["name"] for p in by_search] == ["Bracket"]

    def test_get_single_resource(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        fetched = client.get(f"{RESOURCES}/{resource['id']}").json()
        assert fetched["id"] == resource["id"]
        assert fetched["name"] == "Ferula 1"

    def test_get_unknown_resource_is_404(self, client: TestClient):
        resp = client.get(f"{RESOURCES}/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


class TestUpdateAndStatus:
    def test_non_owner_cannot_update(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        other = make_user("intruder")
        resp = client.put(
            f"{RESOURCES}/{resource['id']}",
            headers=auth_headers(other),
            json={"name": "Hijacked"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"

    def test_owner_updates_and_discontinues(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        updated = client.put(
            f"{RESOURCES}/{resource['id']}", headers=h, json={"featured": True}
        ).json()
        assert updated["featured"] is True
        disc = client.post(
            f"{RESOURCES}/{resource['id']}/discontinue", headers=h
        ).json()
        assert disc["status"] == "discontinued"
        react = client.post(
            f"{RESOURCES}/{resource['id']}/reactivate", headers=h
        ).json()
        assert react["status"] == "active"


class TestArchive:
    def test_archive_blocked_by_open_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        # An open Request referencing the Resource blocks owner-side archive.
        client.post(
            REQUESTS,
            headers=h,
            json={"title": "Campaign", "items": [{"resource_id": resource["id"]}]},
        )
        resp = client.post(f"{RESOURCES}/{resource['id']}/archive", headers=h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_ARCHIVE_BLOCKED"

    def test_owner_archives_unreferenced_resource(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        archived = client.post(
            f"{RESOURCES}/{resource['id']}/archive", headers=h
        ).json()
        assert archived["active"] is False
        # Archived resources drop out of the public catalog.
        assert resource["id"] not in {p["id"] for p in client.get(RESOURCES).json()}

    def test_force_archive_requires_maintainer(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        resp = client.post(
            f"{RESOURCES}/{resource['id']}/force-archive",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 403

    def test_force_archive_closes_open_items(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        request = client.post(
            REQUESTS,
            headers=h,
            json={"title": "Campaign", "items": [{"resource_id": resource["id"]}]},
        ).json()
        resp = client.post(
            f"{RESOURCES}/{resource['id']}/force-archive",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False
        # The open item (and so the request) is now closed (resource_archived).
        detail = client.get(f"{REQUESTS}/{request['id']}").json()
        assert detail["items"][0]["status"] == "closed"
        assert detail["items"][0]["closed_reason"] == "resource_archived"


class TestResourceCategories:
    """Generic-supply forward-compat: category / units / optional source_url."""

    def test_default_category_is_print_3d(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        assert resource["category"] == "print_3d"
        assert resource["units"] == []

    def test_print_3d_requires_source_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        # No category given -> defaults to print_3d -> source_url is required.
        resp = client.post(
            RESOURCES, headers=auth_headers(normal_user), json={"name": "Ferula"}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "SOURCE_URL_REQUIRED"

    def test_non_3d_resource_needs_no_source_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            RESOURCES,
            headers=auth_headers(normal_user),
            json={
                "name": "Agua potable",
                "category": "water",
                "units": ["litros", "litros", "  cajas  "],
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["category"] == "water"
        assert body["source_url"] is None
        # Units are trimmed and de-duplicated case-insensitively.
        assert body["units"] == ["litros", "cajas"]

    def test_list_filters_by_category(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        _create_resource(client, h, name="Ferula 1")
        client.post(RESOURCES, headers=h, json={"name": "Agua", "category": "water"})
        water = client.get(RESOURCES, params={"category": "water"}).json()
        assert [p["name"] for p in water] == ["Agua"]
        prints = client.get(RESOURCES, params={"category": "print_3d"}).json()
        assert [p["name"] for p in prints] == ["Ferula 1"]

    def test_update_to_3d_requires_source_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        water = client.post(
            RESOURCES, headers=h, json={"name": "Agua", "category": "water"}
        ).json()
        resp = client.put(
            f"{RESOURCES}/{water['id']}", headers=h, json={"category": "print_3d"}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "SOURCE_URL_REQUIRED"

    def test_update_to_non_3d_keeps_existing_source_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        updated = client.put(
            f"{RESOURCES}/{resource['id']}", headers=h, json={"category": "other"}
        ).json()
        assert updated["category"] == "other"
        assert updated["source_url"] == "https://example.com/ferula1.stl"
