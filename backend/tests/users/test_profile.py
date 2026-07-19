"""Tests for the self-profile editor and the public profile page.

Covers ``PUT /users/me`` (edit own name/bio/avatar) and the public,
unauthenticated ``GET /users/{username}/profile`` (identity + the projects the
user collaborates on), including the email-never-leaked and moderation-gate
guarantees.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.requests.constants import ModerationStatus
from app.requests.models import Request
from app.users.models import User

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]

USERS = "/api/v1/users"
RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CENTERS = "/api/v1/collection-centers"
CONTRIB = "/api/v1/contributions"


def _setup_item(
    client: TestClient, h: dict[str, str], admin_h: dict[str, str]
) -> tuple[str, str, str]:
    """Create resource + request item + verified center.

    Returns ``(request_id, item_id, center_id)``.
    """
    resource_id = client.post(
        RESOURCES,
        headers=h,
        json={"name": "Ferula", "source_url": "https://x.io/p.stl"},
    ).json()["id"]
    request = client.post(
        REQUESTS,
        headers=h,
        json={
            "title": "Splints for Venezuela",
            "items": [{"resource_id": resource_id, "quantity": 10}],
        },
    ).json()
    center = client.post(
        CENTERS,
        headers=h,
        json={
            "name": "Centro Caracas",
            "address": "Av. 1",
            "country": "Venezuela",
            "city": "Caracas",
            "contact": "x@y.z",
        },
    ).json()
    client.post(f"{CENTERS}/{center['id']}/verify", headers=admin_h)
    return request["id"], request["items"][0]["id"], center["id"]


def _claim(
    client: TestClient, h: dict[str, str], item_id: str, center_id: str
) -> dict[str, Any]:
    """Claim 4 units of ``item_id`` at ``center_id``; assert success."""
    resp = client.post(
        CONTRIB,
        headers=h,
        json={
            "request_item_id": item_id,
            "collection_center_id": center_id,
            "quantity": 4,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestUpdateMyProfile:
    def test_requires_auth(self, client: TestClient):
        assert client.put(f"{USERS}/me", json={}).status_code == 401

    def test_updates_name_and_bio(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        resp = client.put(
            f"{USERS}/me",
            headers=auth_headers(normal_user),
            json={
                "full_name": "Oriana Moreno",
                "bio": "Maker helping print assistive parts.",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["full_name"] == "Oriana Moreno"
        assert body["bio"] == "Maker helping print assistive parts."
        # MeResponse still carries the flag map.
        assert "flags" in body

    def test_blank_strings_clear_fields(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        client.put(f"{USERS}/me", headers=h, json={"full_name": "Set", "bio": "Set"})
        resp = client.put(f"{USERS}/me", headers=h, json={"full_name": "  ", "bio": ""})
        assert resp.status_code == 200
        body = resp.json()
        assert body["full_name"] is None
        assert body["bio"] is None

    def test_saving_name_leaves_the_avatar_untouched(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        """The two saves are independent: neither clobbers the other."""
        h = auth_headers(normal_user)
        client.put(
            f"{USERS}/me/avatar",
            headers=h,
            json={
                "avatar_url": "https://cdn.example.com/a.jpg",
                "avatar_crop_x": 10,
                "avatar_crop_y": 20,
                "avatar_crop_w": 30,
                "avatar_crop_h": 40,
            },
        )
        body = client.put(f"{USERS}/me", headers=h, json={"full_name": "Nina"}).json()
        assert body["full_name"] == "Nina"
        assert body["avatar_url"] == "https://cdn.example.com/a.jpg"
        assert (body["avatar_crop_x"], body["avatar_crop_w"]) == (10, 30)

        # ...and applying a picture keeps the saved name/bio.
        body = client.put(
            f"{USERS}/me/avatar",
            headers=h,
            json={"avatar_url": "https://cdn.example.com/b.jpg"},
        ).json()
        assert body["full_name"] == "Nina"
        assert body["avatar_url"] == "https://cdn.example.com/b.jpg"

    def test_bio_too_long_rejected(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        resp = client.put(
            f"{USERS}/me",
            headers=auth_headers(normal_user),
            json={"bio": "x" * 281},
        )
        assert resp.status_code == 422

    def test_cannot_change_username_or_email(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        # Unknown keys are ignored; username/email stay put.
        resp = client.put(
            f"{USERS}/me",
            headers=auth_headers(normal_user),
            json={"username": "hacked", "email": "new@x.io", "full_name": "Real"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "user1"


class TestUpdateMyAvatar:
    def test_requires_auth(self, client: TestClient):
        assert client.put(f"{USERS}/me/avatar", json={}).status_code == 401

    def test_crop_saved_and_defaults_to_whole_image(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        # Defaults to the whole image (rendered as a centred cover fit).
        body = client.put(f"{USERS}/me/avatar", headers=h, json={}).json()
        assert (body["avatar_crop_x"], body["avatar_crop_y"]) == (0, 0)
        assert (body["avatar_crop_w"], body["avatar_crop_h"]) == (100, 100)

        # A zoomed-in crop: a small square from the middle of the picture.
        resp = client.put(
            f"{USERS}/me/avatar",
            headers=h,
            json={
                "avatar_url": "https://cdn.example.com/a.jpg",
                "avatar_crop_x": 30,
                "avatar_crop_y": 10.5,
                "avatar_crop_w": 25,
                "avatar_crop_h": 40,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["avatar_url"] == "https://cdn.example.com/a.jpg"
        assert (body["avatar_crop_x"], body["avatar_crop_y"]) == (30, 10.5)
        assert (body["avatar_crop_w"], body["avatar_crop_h"]) == (25, 40)
        # Exposed publicly so the avatar crops identically for every viewer.
        public = client.get(f"{USERS}/user1/profile").json()["user"]
        assert (public["avatar_crop_x"], public["avatar_crop_w"]) == (30, 25)
        assert (public["avatar_crop_y"], public["avatar_crop_h"]) == (10.5, 40)

    def test_null_url_removes_the_picture(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        client.put(
            f"{USERS}/me/avatar",
            headers=h,
            json={"avatar_url": "https://cdn.example.com/a.jpg"},
        )
        body = client.put(f"{USERS}/me/avatar", headers=h, json={}).json()
        assert body["avatar_url"] is None

    def test_crop_out_of_range_rejected(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        for payload in (
            {"avatar_crop_x": 101},
            {"avatar_crop_y": -1},
            # A zero-size crop would divide by zero when rendering.
            {"avatar_crop_w": 0},
            {"avatar_crop_h": 101},
        ):
            resp = client.put(f"{USERS}/me/avatar", headers=h, json=payload)
            assert resp.status_code == 422, payload


class TestPublicProfile:
    def test_public_no_auth(
        self,
        client: TestClient,
        normal_user: User,
    ):
        resp = client.get(f"{USERS}/user1/profile")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["username"] == "user1"
        assert body["projects"] == []
        assert body["projects_count"] == 0

    def test_never_exposes_email(
        self,
        client: TestClient,
        normal_user: User,
        db: Session,
    ):
        normal_user.email = "secret@example.com"
        db.commit()
        resp = client.get(f"{USERS}/user1/profile")
        assert resp.status_code == 200
        assert "email" not in resp.json()["user"]

    def test_case_insensitive_handle(
        self,
        client: TestClient,
        normal_user: User,
    ):
        assert client.get(f"{USERS}/USER1/profile").status_code == 200

    def test_unknown_user_404(self, client: TestClient):
        resp = client.get(f"{USERS}/nobody-here/profile")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "USER_NOT_FOUND"

    def test_deactivated_user_404(
        self,
        client: TestClient,
        make_user: MakeUser,
    ):
        make_user("ghost", active=False)
        assert client.get(f"{USERS}/ghost/profile").status_code == 404

    def test_anonymous_system_account_404(
        self,
        client: TestClient,
        make_user: MakeUser,
    ):
        make_user("anonymous")
        assert client.get(f"{USERS}/anonymous/profile").status_code == 404

    def test_projects_card_from_contributions(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        _, item_id, center_id = _setup_item(client, h, auth_headers(admin_user))
        _claim(client, h, item_id, center_id)
        resp = client.get(f"{USERS}/user1/profile")
        assert resp.status_code == 200
        body = resp.json()
        assert body["projects_count"] == 1
        project = body["projects"][0]
        assert project["request_title"] == "Splints for Venezuela"
        assert project["resource_name"] == "Ferula"
        assert project["status"] == "claimed"
        assert project["quantity"] == 4
        assert project["collection_center_country"] == "Venezuela"
        assert project["item_number"] == 1

    @pytest.mark.moderation
    def test_unpublished_campaign_hidden_from_profile(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        # The moderation mark opts out of the autouse auto-publish, so the
        # campaign is born unpublished; approve it directly before claiming
        # (contributions on unpublished campaigns are rejected).
        h = auth_headers(normal_user)
        request_id, item_id, center_id = _setup_item(
            client, h, auth_headers(admin_user)
        )
        request = db.query(Request).filter(Request.id == request_id).first()
        assert request is not None
        request.moderation_status = ModerationStatus.APPROVED
        db.commit()

        _claim(client, h, item_id, center_id)
        assert client.get(f"{USERS}/user1/profile").json()["projects_count"] == 1

        # Pull it back to pending: it must vanish from the public profile.
        request.moderation_status = ModerationStatus.PENDING
        db.commit()
        assert client.get(f"{USERS}/user1/profile").json()["projects_count"] == 0
