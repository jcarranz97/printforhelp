"""Tests for the item-tracking (QR provenance) endpoints."""

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.tracking import qr, service
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
    client: TestClient,
    maker_h: dict[str, str],
    admin_h: dict[str, str],
    qty: int = 3,
    label_url: str | None = None,
    labels_per_page: int | None = None,
) -> dict[str, Any]:
    """Create a resource + request item + verified center, then claim it."""
    resource_body: dict[str, Any] = {
        "name": "Ferula",
        "source_url": "https://x.io/p.stl",
    }
    if label_url is not None:
        resource_body["label_image_url"] = label_url
    if labels_per_page is not None:
        resource_body["labels_per_page"] = labels_per_page
    resource_id = client.post(
        RESOURCES,
        headers=maker_h,
        json=resource_body,
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
        assert body["visibility"] == "public"

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


class TestQuantitySync:
    """A quantity edit reconciles the per-unit QRs (contributions PATCH)."""

    def test_growing_appends_units_and_keeps_printed_tokens(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=2)
        before = _generate(client, h, contribution["id"])
        original = {i["sequence"]: i["tracking_token"] for i in before["items"]}

        resp = client.patch(
            f"{CONTRIB}/{contribution['id']}", headers=h, json={"quantity": 4}
        )
        assert resp.status_code == 200, resp.text

        after = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        assert after["quantity"] == 4
        assert [i["sequence"] for i in after["items"]] == [1, 2, 3, 4]
        # Units 1-2 keep the exact tokens whose labels may already be printed.
        for item in after["items"]:
            if item["sequence"] in original:
                assert item["tracking_token"] == original[item["sequence"]]

    def test_shrinking_retires_trailing_units(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        before = _generate(client, h, contribution["id"])
        retired = next(i for i in before["items"] if i["sequence"] == 3)

        resp = client.patch(
            f"{CONTRIB}/{contribution['id']}", headers=h, json={"quantity": 2}
        )
        assert resp.status_code == 200, resp.text

        after = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        assert [i["sequence"] for i in after["items"]] == [1, 2]
        # The surplus unit's QR stops resolving publicly.
        assert client.get(f"{TRACK}/{retired['tracking_token']}").status_code == 404

    def test_regrowing_revives_the_same_tokens(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """Shrink then grow: an already-printed label for unit 3 still works."""
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        before = _generate(client, h, contribution["id"])
        unit3 = next(i for i in before["items"] if i["sequence"] == 3)

        client.patch(f"{CONTRIB}/{contribution['id']}", headers=h, json={"quantity": 1})
        client.patch(f"{CONTRIB}/{contribution['id']}", headers=h, json={"quantity": 3})

        after = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        assert [i["sequence"] for i in after["items"]] == [1, 2, 3]
        revived = next(i for i in after["items"] if i["sequence"] == 3)
        assert revived["tracking_token"] == unit3["tracking_token"]
        assert client.get(f"{TRACK}/{unit3['tracking_token']}").status_code == 200

    def test_edit_without_tracking_is_a_noop(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=2)
        resp = client.patch(
            f"{CONTRIB}/{contribution['id']}", headers=h, json={"quantity": 6}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["quantity"] == 6
        # Generating afterwards still produces one QR per unit.
        assert len(_generate(client, h, contribution["id"])["items"]) == 6


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
        client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "private"},
        )
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
        group = _generate(client, h, contribution["id"])
        client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "private"},
        )
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

    def test_bundle_scope_filters_qrs(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        # With 2 units the bundles differ: group (1 QR), individual (2 QRs),
        # both (3 QRs), so the rendered bytes must not match across scopes.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=2)
        group = _generate(client, h, contribution["id"])
        gid = group["group_id"]
        renders: dict[str, bytes] = {}
        for scope in ("group", "individual", "both"):
            resp = client.get(
                f"{TRACKING}/groups/{gid}/qr-bundle.png",
                params={"scope": scope},
                headers=h,
            )
            assert resp.status_code == 200, resp.text
            assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"
            renders[scope] = resp.content
        assert renders["group"] != renders["individual"]
        assert renders["group"] != renders["both"]
        assert renders["individual"] != renders["both"]
        # No scope param defaults to "both" (the historical behavior).
        default = client.get(f"{TRACKING}/groups/{gid}/qr-bundle.png", headers=h)
        assert default.content == renders["both"]

    def test_bundle_rejects_unknown_scope(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        group = _generate(client, h, contribution["id"])
        resp = client.get(
            f"{TRACKING}/groups/{group['group_id']}/qr-bundle.png",
            params={"scope": "bogus"},
            headers=h,
        )
        assert resp.status_code == 422

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


def _png_size(data: bytes) -> tuple[int, int]:
    """Return the (width, height) of PNG bytes."""
    return Image.open(io.BytesIO(data)).size


def _write_media_png(name: str) -> str:
    """Write a tiny PNG under MEDIA_ROOT and return its public /media URL."""
    path = Path(settings.MEDIA_ROOT) / "images" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (600, 160), (200, 40, 40)).save(path)
    return f"http://testserver/media/images/{name}"


class TestLabelBundle:
    def test_message_bundle_renders_pdf_and_png(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        # No custom message set → the default community message is printed.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=2)
        gid = _generate(client, h, contribution["id"])["group_id"]

        pdf = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.pdf",
            headers=h,
            params={"message": "true"},
        )
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

        png = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.png",
            headers=h,
            params={"message": "true"},
        )
        assert png.status_code == 200
        assert png.content[:8] == b"\x89PNG\r\n\x1a\n"

        # The message flag draws the note above each QR, growing every cell —
        # so the sheet is a different size than the plain QR grid.
        plain = client.get(f"{TRACKING}/groups/{gid}/qr-bundle.png", headers=h)
        assert _png_size(png.content) != _png_size(plain.content)

    def test_label_bundle_uses_resource_label(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        label_url = _write_media_png("bundle-label.png")
        contribution = _setup_contribution(
            client, h, admin_h, qty=2, label_url=label_url
        )
        gid = _generate(client, h, contribution["id"])["group_id"]

        # Owner view surfaces the label so the UI can offer the checkbox.
        owner = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        assert owner["resource_label_image_url"] == label_url

        pdf = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.pdf",
            headers=h,
            params={"labels": "true", "message": "true"},
        )
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

    def test_saved_messages_are_user_owned_and_reusable(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        # Save a template (trimmed); saving the same text again dedupes.
        first = client.post(
            f"{TRACKING}/messages", headers=h, json={"body": "  Hecho con amor  "}
        )
        assert first.status_code == 201, first.text
        assert first.json()["body"] == "Hecho con amor"
        again = client.post(
            f"{TRACKING}/messages", headers=h, json={"body": "Hecho con amor"}
        )
        assert again.json()["id"] == first.json()["id"]

        client.post(f"{TRACKING}/messages", headers=h, json={"body": "Gracias"})
        listing = client.get(f"{TRACKING}/messages", headers=h)
        assert [m["body"] for m in listing.json()] == ["Gracias", "Hecho con amor"]

        # The list is per-user: a different user sees none of them.
        other = auth_headers(make_user("other-maker"))
        assert client.get(f"{TRACKING}/messages", headers=other).json() == []

        # Delete removes it; deleting someone else's (or unknown) is a 404.
        assert (
            client.delete(
                f"{TRACKING}/messages/{first.json()['id']}", headers=h
            ).status_code
            == 204
        )
        assert [
            m["body"] for m in client.get(f"{TRACKING}/messages", headers=h).json()
        ] == ["Gracias"]
        assert (
            client.delete(
                f"{TRACKING}/messages/{first.json()['id']}", headers=other
            ).status_code
            == 404
        )

    def test_message_text_drives_bundle_without_saving(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        # The live textarea content renders into the bundle and is not saved.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=1)
        gid = _generate(client, h, contribution["id"])["group_id"]

        resp = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.pdf",
            headers=h,
            params={"message": "true", "message_text": "Unsaved note"},
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
        # Downloading never persists a saved message.
        assert client.get(f"{TRACKING}/messages", headers=h).json() == []

    def test_load_label_image_helpers(self):
        assert service.load_label_image(None) is None
        assert service.load_label_image("http://x/media/images/missing.png") is None
        url = _write_media_png("helper-label.png")
        image = service.load_label_image(url)
        assert image is not None
        assert image.size == (600, 160)

    def test_label_pages_precede_qr_pages(self):
        # With a label folded in, the PDF prints a stack of label copies
        # first, then the QR grid — so it has more pages than the plain grid.
        label = Image.new("RGB", (800, 200), (10, 20, 30))
        labels = [(f"#{i}", f"https://x.test/track/t{i}") for i in range(12)]
        label_pages = qr.build_label_pages(label, len(labels))
        assert len(label_pages) >= 1
        expected = (round(210 * 150 / 25.4), round(297 * 150 / 25.4))
        assert all(page.size == expected for page in label_pages)

        with_label = qr.bundle_pdf_bytes(labels, label, "Un mensaje de prueba " * 6)
        without_label = qr.bundle_pdf_bytes(labels, None, None)
        assert with_label[:4] == b"%PDF"
        assert len(with_label) > len(without_label)

        # The PNG stacks the label grid above the QR grid on one taller sheet.
        with_label_png = qr.bundle_png_bytes(labels, label, "Hola")
        without_label_png = qr.bundle_png_bytes(labels, None, None)
        assert _png_size(with_label_png)[1] > _png_size(without_label_png)[1]

        # A single-copy label still produces one clean page.
        sheet = qr.build_label_sheet(label, 1)
        assert sheet.width > 0
        assert sheet.height > 0

    def test_labels_per_page_controls_tile_size_and_pagination(self):
        # A wide banner label. Asking for 2 per page must make each copy far
        # larger (and pack fewer per page) than 8 per page.
        label = Image.new("RGB", (800, 200), (10, 20, 30))
        labels = [(f"#{i}", f"https://x.test/track/t{i}") for i in range(9)]

        two = qr.build_label_pages(label, len(labels), per_page=2)
        eight = qr.build_label_pages(label, len(labels), per_page=8)
        # 9 copies at 2/page = 5 pages; at 8/page = 2 pages.
        assert len(two) == 5
        assert len(eight) == 2

        # The grid helper sizes a bigger tile for fewer-per-page.
        _, _, tile_two = qr._label_grid(label, 2)
        _, _, tile_eight = qr._label_grid(label, 8)
        assert tile_two.height > tile_eight.height

        # A square label should prefer a balanced grid over a single column.
        square = Image.new("RGB", (400, 400), (0, 0, 0))
        cols, rows, _ = qr._label_grid(square, 6)
        assert cols > 1
        assert rows > 1

        # The on-screen preview honors per_page for its column count too.
        preview = qr.build_label_sheet(label, len(labels), per_page=2)
        assert preview.width > 0
        assert preview.height > 0

    def test_cut_guides_drawn_between_label_copies(self):
        # A white label leaves the page blank except for the dashed cut guides,
        # so their color appearing proves the gaps are delimited.
        label = Image.new("RGB", (600, 450), "white")
        page = qr.build_label_pages(label, 4, per_page=4)[0]
        colors = {color for _, color in (page.getcolors(1 << 24) or [])}
        assert qr._CUT_COLOR in colors

        # A single copy has nothing to separate, so no guides are drawn.
        solo = qr.build_label_pages(label, 1, per_page=1)[0]
        solo_colors = {color for _, color in (solo.getcolors(1 << 24) or [])}
        assert qr._CUT_COLOR not in solo_colors

    def test_labels_per_page_flows_into_bundle_endpoints(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        label_url = _write_media_png("per-page-label.png")
        contribution = _setup_contribution(
            client, h, admin_h, qty=3, label_url=label_url, labels_per_page=2
        )
        gid = _generate(client, h, contribution["id"])["group_id"]

        pdf = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.pdf",
            headers=h,
            params={"labels": "true"},
        )
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

        png = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.png",
            headers=h,
            params={"labels": "true"},
        )
        assert png.status_code == 200
        assert png.content[:8] == b"\x89PNG\r\n\x1a\n"


NOTIFICATIONS = "/api/v1/notifications"
WATCHES = "/api/v1/watches"


def _notifications(client: TestClient, headers: dict[str, str]) -> list[dict[str, Any]]:
    resp = client.get(NOTIFICATIONS, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestWatchNotifications:
    def _public_group(self, client, h, admin_h) -> dict[str, Any]:
        contribution = _setup_contribution(client, h, admin_h)
        group = _generate(client, h, contribution["id"])
        client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "public"},
        )
        return group

    def test_maker_auto_watches_and_is_notified(
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

        # A different logged-in user posts an update after scanning.
        scanner = auth_headers(make_user("scanner"))
        record = client.post(
            f"{TRACK}/{token}/records",
            headers=scanner,
            json={"description": "Arrived at the airport"},
        )
        assert record.status_code == 201
        record_id = record.json()["id"]

        notes = _notifications(client, h)
        assert len(notes) == 1
        note = notes[0]
        assert note["event"] == "tracking_update"
        assert note["reason"] == "watch"
        assert note["entity_type"] == "tracking_group"
        assert note["actor"]["username"] == "scanner"
        assert note["link"] == f"/track/{token}"
        assert note["title"] == "Ferula"
        # The notification deep-links to and highlights the exact update.
        assert note["anchor"] == f"record-{record_id}"

    def test_guest_record_notifies_maker(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        token = group["tracking_token"]

        # A guest (no auth) posts; the maker is still notified.
        assert (
            client.post(
                f"{TRACK}/{token}/records",
                json={"description": "Someone found it"},
            ).status_code
            == 201
        )

        notes = _notifications(client, h)
        assert len(notes) == 1
        assert notes[0]["event"] == "tracking_update"
        assert notes[0]["actor"]["username"] == "anonymous"

    def test_maker_own_record_is_not_self_notified(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        token = group["tracking_token"]

        client.post(
            f"{TRACK}/{token}/records", headers=h, json={"description": "Printed it"}
        )
        assert _notifications(client, h) == []

    def test_extra_watcher_gets_notified(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        token, group_id = group["tracking_token"], group["group_id"]

        # A logged-in bystander opts in via the generic watch endpoint.
        watcher = make_user("watcher")
        watcher_h = auth_headers(watcher)
        assert (
            client.post(
                WATCHES,
                headers=watcher_h,
                json={"entity_type": "tracking_group", "entity_id": group_id},
            ).status_code
            == 204
        )

        client.post(
            f"{TRACK}/{token}/records", json={"description": "Handed to a courier"}
        )

        # Both the maker and the opted-in watcher are notified.
        assert len(_notifications(client, h)) == 1
        assert len(_notifications(client, watcher_h)) == 1

        # After unwatching, no new notification lands.
        assert (
            client.delete(
                f"{WATCHES}/tracking_group/{group_id}", headers=watcher_h
            ).status_code
            == 204
        )
        client.post(f"{TRACK}/{token}/records", json={"description": "Delivered"})
        assert len(_notifications(client, watcher_h)) == 1
        assert len(_notifications(client, h)) == 2

    def test_public_view_exposes_group_id_and_watch_state(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        group = self._public_group(client, h, admin_h)
        token, group_id = group["tracking_token"], group["group_id"]

        # Guests see the group id but never a watch state.
        guest_view = client.get(f"{TRACK}/{token}").json()
        assert guest_view["group_id"] == group_id
        assert guest_view["watching"] is False

        bystander_h = auth_headers(make_user("bystander"))
        assert (
            client.get(f"{TRACK}/{token}", headers=bystander_h).json()["watching"]
            is False
        )
        client.post(
            WATCHES,
            headers=bystander_h,
            json={"entity_type": "tracking_group", "entity_id": group_id},
        )
        assert (
            client.get(f"{TRACK}/{token}", headers=bystander_h).json()["watching"]
            is True
        )

    def test_owner_view_reports_auto_watch(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        group = _generate(client, h, contribution["id"])
        owner_view = client.get(
            f"{TRACKING}/contributions/{group['contribution_id']}", headers=h
        ).json()
        assert owner_view["watching"] is True
