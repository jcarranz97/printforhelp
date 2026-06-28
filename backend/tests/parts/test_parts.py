"""Tests for the Part catalog endpoints (Phase 4)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User

PARTS = "/api/v1/parts"
REQUESTS = "/api/v1/requests"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _create_part(
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
    resp = client.post(PARTS, headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreatePart:
    def test_requires_auth(self, client: TestClient):
        assert client.post(PARTS, json={}).status_code == 401

    def test_invalid_body_is_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(PARTS, headers=auth_headers(normal_user), json={})
        assert resp.status_code == 422

    def test_rejects_non_http_source_url(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            PARTS,
            headers=auth_headers(normal_user),
            json={"name": "x", "source_url": "ftp://nope"},
        )
        assert resp.status_code == 422

    def test_owner_defaults_to_caller(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        part = _create_part(client, auth_headers(normal_user))
        assert part["owner_user_id"] == str(normal_user.id)
        assert part["owner_organization_id"] is None
        assert part["creator_id"] == str(normal_user.id)
        assert part["status"] == "active"
        assert part["image_url"] == "https://example.com/ferula1.png"


class TestListAndGetParts:
    def test_list_filters_by_tag_and_search(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        _create_part(client, h, name="Ferula 1", tags=["ferula"])
        _create_part(client, h, name="Bracket", tags=["other"])
        by_tag = client.get(PARTS, params={"tag": "ferula"}).json()
        assert [p["name"] for p in by_tag] == ["Ferula 1"]
        by_search = client.get(PARTS, params={"search": "brack"}).json()
        assert [p["name"] for p in by_search] == ["Bracket"]

    def test_get_single_part(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        part = _create_part(client, auth_headers(normal_user))
        fetched = client.get(f"{PARTS}/{part['id']}").json()
        assert fetched["id"] == part["id"]
        assert fetched["name"] == "Ferula 1"

    def test_get_unknown_part_is_404(self, client: TestClient):
        resp = client.get(f"{PARTS}/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PART_NOT_FOUND"


class TestUpdateAndStatus:
    def test_non_owner_cannot_update(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        part = _create_part(client, auth_headers(normal_user))
        other = make_user("intruder")
        resp = client.put(
            f"{PARTS}/{part['id']}",
            headers=auth_headers(other),
            json={"name": "Hijacked"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"

    def test_owner_updates_and_discontinues(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part = _create_part(client, h)
        updated = client.put(
            f"{PARTS}/{part['id']}", headers=h, json={"featured": True}
        ).json()
        assert updated["featured"] is True
        disc = client.post(f"{PARTS}/{part['id']}/discontinue", headers=h).json()
        assert disc["status"] == "discontinued"
        react = client.post(f"{PARTS}/{part['id']}/reactivate", headers=h).json()
        assert react["status"] == "active"


class TestArchive:
    def test_archive_blocked_by_open_request(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part = _create_part(client, h)
        # An open Request referencing the Part blocks owner-side archive.
        client.post(
            REQUESTS,
            headers=h,
            json={"title": "Campaign", "items": [{"part_id": part["id"]}]},
        )
        resp = client.post(f"{PARTS}/{part['id']}/archive", headers=h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PART_ARCHIVE_BLOCKED"

    def test_owner_archives_unreferenced_part(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        part = _create_part(client, h)
        archived = client.post(f"{PARTS}/{part['id']}/archive", headers=h).json()
        assert archived["active"] is False
        # Archived parts drop out of the public catalog.
        assert part["id"] not in {p["id"] for p in client.get(PARTS).json()}

    def test_force_archive_requires_maintainer(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        part = _create_part(client, auth_headers(normal_user))
        resp = client.post(
            f"{PARTS}/{part['id']}/force-archive",
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
        part = _create_part(client, h)
        request = client.post(
            REQUESTS,
            headers=h,
            json={"title": "Campaign", "items": [{"part_id": part["id"]}]},
        ).json()
        resp = client.post(
            f"{PARTS}/{part['id']}/force-archive", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False
        # The open item (and so the request) is now closed (part_archived).
        detail = client.get(f"{REQUESTS}/{request['id']}").json()
        assert detail["items"][0]["status"] == "closed"
        assert detail["items"][0]["closed_reason"] == "part_archived"
