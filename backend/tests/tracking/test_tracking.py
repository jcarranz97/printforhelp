"""Tests for the item-tracking (QR provenance) endpoints."""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.tracking import qr
from app.users.constants import UserRole
from app.users.models import User

RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CENTERS = "/api/v1/collection-centers"
CONTRIB = "/api/v1/contributions"
TRACKING = "/api/v1/tracking"
TRACK = "/api/v1/track"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _setup_contribution(
    client: TestClient, maker_h: dict[str, str], admin_h: dict[str, str], qty: int = 3
) -> dict[str, Any]:
    """Create a resource + request item + verified center, then claim it."""
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
            "items": [{"resource_id": resource_id, "quantity": 20}],
        },
    ).json()["items"][0]["id"]
    cc = client.post(
        CENTERS,
        headers=maker_h,
        json={
            "name": "Centro",
            "address": "Av. 1",
            "country": "VE",
            "city": "Caracas",
            "contact": "x@y.z",
        },
    ).json()
    client.post(f"{CENTERS}/{cc['id']}/verify", headers=admin_h)
    resp = client.post(
        CONTRIB,
        headers=maker_h,
        json={
            "request_item_id": item_id,
            "collection_center_id": cc["id"],
            "quantity": qty,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _generate(
    client: TestClient, h: dict[str, str], contribution_id: str
) -> dict[str, Any]:
    resp = client.post(f"{TRACKING}/contributions/{contribution_id}", headers=h)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestGenerate:
    def test_requires_auth(self, client: TestClient):
        assert client.post(f"{TRACKING}/contributions/{'0' * 8}").status_code in (
            401,
            422,
        )

    def test_generates_group_and_one_item_per_unit(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        body = _generate(client, h, contribution["id"])
        assert body["quantity"] == 3
        assert len(body["items"]) == 3
        assert [i["sequence"] for i in body["items"]] == [1, 2, 3]
        # Group token differs from every item token, all unique.
        tokens = {body["tracking_token"], *(i["tracking_token"] for i in body["items"])}
        assert len(tokens) == 4
        assert body["visibility"] == "private"

    def test_only_maker_or_admin(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        other = auth_headers(make_user("intruder"))
        resp = client.post(
            f"{TRACKING}/contributions/{contribution['id']}", headers=other
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TRACKING_FORBIDDEN"

    def test_admin_can_generate_for_others(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        assert (
            client.post(
                f"{TRACKING}/contributions/{contribution['id']}", headers=admin_h
            ).status_code
            == 201
        )

    def test_conflict_when_already_tracked(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        _generate(client, h, contribution["id"])
        resp = client.post(f"{TRACKING}/contributions/{contribution['id']}", headers=h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "TRACKING_ALREADY_EXISTS"

    def test_unknown_contribution_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resp = client.post(
            f"{TRACKING}/contributions/00000000-0000-0000-0000-000000000000",
            headers=h,
        )
        assert resp.status_code == 404


class TestOwnerView:
    def test_shows_token_on_my_contributions(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        # Before generating: token is null.
        me = client.get(f"{CONTRIB}/me", headers=h).json()
        assert me[0]["tracking_token"] is None
        group = _generate(client, h, contribution["id"])
        me = client.get(f"{CONTRIB}/me", headers=h).json()
        assert me[0]["tracking_token"] == group["tracking_token"]

    def test_owner_view_404_without_tracking(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        resp = client.get(f"{TRACKING}/contributions/{contribution['id']}", headers=h)
        assert resp.status_code == 404


class TestVisibility:
    def _tracked(self, client, h, admin_h) -> dict[str, Any]:
        contribution = _setup_contribution(client, h, admin_h)
        return _generate(client, h, contribution["id"])

    def test_private_blocks_guest_allows_owner(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._tracked(client, h, admin_h)
        token = group["tracking_token"]
        assert client.get(f"{TRACK}/{token}").status_code == 403
        owner = client.get(f"{TRACK}/{token}", headers=h)
        assert owner.status_code == 200
        assert owner.json()["can_contribute"] is True

    def test_public_allows_guest(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._tracked(client, h, admin_h)
        resp = client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "public"},
        )
        assert resp.status_code == 200
        token = group["tracking_token"]
        assert client.get(f"{TRACK}/{token}").status_code == 200

    def test_group_allows_named_member_only(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        friend = make_user("friend")
        stranger = make_user("stranger")
        group = self._tracked(client, h, admin_h)
        client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "group", "member_usernames": ["friend", "ghost"]},
        )
        token = group["tracking_token"]
        friend_view = client.get(f"{TRACK}/{token}", headers=auth_headers(friend))
        assert friend_view.status_code == 200
        assert (
            client.get(f"{TRACK}/{token}", headers=auth_headers(stranger)).status_code
            == 403
        )
        # Unknown username "ghost" is silently ignored, only "friend" stuck.
        owner_view = client.get(
            f"{TRACKING}/contributions/{group['contribution_id']}", headers=h
        ).json()
        assert [m["username"] for m in owner_view["members"]] == ["friend"]

    def test_item_token_resolves(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._tracked(client, h, admin_h)
        client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "public"},
        )
        item_token = group["items"][0]["tracking_token"]
        resp = client.get(f"{TRACK}/{item_token}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_kind"] == "item"
        assert body["item_sequence"] == 1

    def test_unknown_token_404(self, client: TestClient):
        assert client.get(f"{TRACK}/does-not-exist").status_code == 404


class TestRecords:
    def _public_group(self, client, h, admin_h) -> dict[str, Any]:
        contribution = _setup_contribution(client, h, admin_h)
        group = _generate(client, h, contribution["id"])
        client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "public"},
        )
        return group

    def test_guest_adds_anonymous_record(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        token = group["tracking_token"]
        resp = client.post(
            f"{TRACK}/{token}/records",
            json={"description": "Left Miami", "tags": ["in-transit", "in-transit"]},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["author"]["username"] is None
        assert body["tags"] == ["in-transit"]
        assert body["can_edit_tags"] is False

    def test_group_timeline_folds_in_item_updates(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        group_token = group["tracking_token"]
        item_token = group["items"][0]["tracking_token"]
        client.post(f"{TRACK}/{group_token}/records", json={"description": "group up"})
        client.post(f"{TRACK}/{item_token}/records", json={"description": "item up"})

        # Default: the group timeline includes the item update, labeled by unit.
        both = client.get(f"{TRACK}/{group_token}").json()["records"]
        assert len(both) == 2
        item_record = next(r for r in both if r["target_kind"] == "item")
        assert item_record["item_sequence"] == 1
        assert item_record["target_token"] == item_token

        # Scoped to group only: just the group-level update.
        only_group = client.get(
            f"{TRACK}/{group_token}", params={"include_item_updates": "false"}
        ).json()["records"]
        assert len(only_group) == 1
        assert only_group[0]["target_kind"] == "group"

    def test_logged_in_attribution_toggle(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        token = group["tracking_token"]
        scanner = make_user("scanner")
        named = client.post(
            f"{TRACK}/{token}/records",
            headers=auth_headers(scanner),
            json={"description": "seen", "display_anonymous": False},
        ).json()
        assert named["author"]["username"] == "scanner"
        hidden = client.post(
            f"{TRACK}/{token}/records",
            headers=auth_headers(scanner),
            json={"description": "seen again", "display_anonymous": True},
        ).json()
        assert hidden["author"]["username"] is None

    def test_private_blocks_guest_records(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        group = _generate(client, h, contribution["id"])  # private
        resp = client.post(
            f"{TRACK}/{group['tracking_token']}/records",
            json={"description": "nope"},
        )
        assert resp.status_code == 403

    def test_edit_tags_permissions(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        token = group["tracking_token"]
        scanner = make_user("scanner")
        record = client.post(
            f"{TRACK}/{token}/records",
            headers=auth_headers(scanner),
            json={"description": "seen", "display_anonymous": False},
        ).json()
        rid = record["id"]
        # A stranger cannot edit.
        stranger = auth_headers(make_user("stranger"))
        assert (
            client.patch(
                f"{TRACKING}/records/{rid}", headers=stranger, json={"tags": ["x"]}
            ).status_code
            == 403
        )
        # The author can.
        assert (
            client.patch(
                f"{TRACKING}/records/{rid}",
                headers=auth_headers(scanner),
                json={"tags": ["received"]},
            ).status_code
            == 200
        )
        # The contribution owner can edit even an anonymous scanner's record.
        owner_edit = client.patch(
            f"{TRACKING}/records/{rid}", headers=h, json={"tags": ["owner-tag"]}
        )
        assert owner_edit.status_code == 200
        assert owner_edit.json()["tags"] == ["owner-tag"]
        # Owner sees can_edit_tags true on the owner view timeline.
        owner_view = client.get(
            f"{TRACKING}/contributions/{group['contribution_id']}", headers=h
        ).json()
        assert owner_view["records"][0]["can_edit_tags"] is True

    def test_edit_unknown_record_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.patch(
            f"{TRACKING}/records/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(normal_user),
            json={"tags": ["x"]},
        )
        assert resp.status_code == 404

    def test_edit_item_record_tags(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        item_token = group["items"][0]["tracking_token"]
        record = client.post(
            f"{TRACK}/{item_token}/records", json={"description": "unit 1"}
        ).json()
        # The owner can retag an anonymous item-level record.
        resp = client.patch(
            f"{TRACKING}/records/{record['id']}", headers=h, json={"tags": ["fixed"]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tags"] == ["fixed"]
        assert body["target_kind"] == "item"
        assert body["target_token"] == item_token
        assert body["item_sequence"] == 1

    def test_item_record_scoped_to_item(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        item_token = group["items"][0]["tracking_token"]
        other_item_token = group["items"][1]["tracking_token"]
        client.post(
            f"{TRACK}/{item_token}/records", json={"description": "unit 1 update"}
        )
        # The record shows on item 1 but not item 2.
        assert len(client.get(f"{TRACK}/{item_token}").json()["records"]) == 1
        assert len(client.get(f"{TRACK}/{other_item_token}").json()["records"]) == 0
        # The owner timeline aggregates all item records.
        owner_view = client.get(
            f"{TRACKING}/contributions/{group['contribution_id']}", headers=h
        ).json()
        assert owner_view["records"][0]["target_kind"] == "item"
        assert owner_view["records"][0]["item_sequence"] == 1


class TestQr:
    def test_token_qr_png(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        group = _generate(client, h, contribution["id"])
        resp = client.get(f"{TRACK}/{group['tracking_token']}/qr.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_qr_unknown_token_404(self, client: TestClient):
        assert client.get(f"{TRACK}/nope/qr.png").status_code == 404

    def test_pdf_paginates_onto_a4_pages(self):
        # More cells than fit on one A4 page must spill onto further pages.
        labels = [(f"#{i}", f"https://x.test/track/tok{i}") for i in range(40)]
        pages = qr.build_pdf_pages(labels)
        assert len(pages) >= 2
        # Every page is A4 at 150 DPI (210 x 297 mm).
        expected = (round(210 * 150 / 25.4), round(297 * 150 / 25.4))
        assert all(page.size == expected for page in pages)

    def test_bundle_png_and_pdf(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=2)
        group = _generate(client, h, contribution["id"])
        gid = group["group_id"]
        png = client.get(f"{TRACKING}/groups/{gid}/qr-bundle.png", headers=h)
        assert png.status_code == 200
        assert png.content[:8] == b"\x89PNG\r\n\x1a\n"
        pdf = client.get(f"{TRACKING}/groups/{gid}/qr-bundle.pdf", headers=h)
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

    def test_bundle_requires_owner(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        group = _generate(client, h, contribution["id"])
        intruder = auth_headers(make_user("intruder", UserRole.USER))
        assert (
            client.get(
                f"{TRACKING}/groups/{group['group_id']}/qr-bundle.png", headers=intruder
            ).status_code
            == 403
        )
