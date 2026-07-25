"""Tests for the item-tracking (QR provenance) endpoints."""

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

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
    center_h: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a resource + request item + verified center, then claim it.

    ``center_h`` owns the drop-off center; it defaults to the maker, who is
    then an effective member of their own center (and so auto-receives on
    delivery). Pass a different user to model the usual split.
    """
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
        headers=center_h or maker_h,
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

    def test_regrowing_mints_fresh_tokens_and_leaves_retired_ones_dead(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """Shrink then grow: unit 3 comes back as a *new* QR, not the old one.

        A label printed for the original unit 3 was thrown away with the units
        that never arrived, so reviving its token would point a stray sticker
        at a different physical piece.
        """
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        before = _generate(client, h, contribution["id"])
        unit3 = next(i for i in before["items"] if i["sequence"] == 3)
        unit1 = next(i for i in before["items"] if i["sequence"] == 1)

        client.patch(f"{CONTRIB}/{contribution['id']}", headers=h, json={"quantity": 1})
        client.patch(f"{CONTRIB}/{contribution['id']}", headers=h, json={"quantity": 3})

        after = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        assert [i["sequence"] for i in after["items"]] == [1, 2, 3]
        regrown = next(i for i in after["items"] if i["sequence"] == 3)
        assert regrown["tracking_token"] != unit3["tracking_token"]
        # The retired token stays dead; the new one resolves.
        assert client.get(f"{TRACK}/{unit3['tracking_token']}").status_code == 404
        assert client.get(f"{TRACK}/{regrown['tracking_token']}").status_code == 200
        # Unit 1 was never retired, so its printed label is untouched.
        assert (
            next(i for i in after["items"] if i["sequence"] == 1)["tracking_token"]
            == unit1["tracking_token"]
        )

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


class TestCommitmentsListToken:
    """The item's commitments list exposes the token to maintainers only."""

    def _commitments_url(self, client: TestClient, h: dict[str, str]) -> str:
        """The public commitments endpoint for the caller's only contribution."""
        mine = client.get(f"{CONTRIB}/me", headers=h).json()[0]
        return (
            f"{REQUESTS}/{mine['request_id']}/items/{mine['item_number']}/contributions"
        )

    def test_maintainer_sees_token_others_do_not(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h)
        url = self._commitments_url(client, h)
        maintainer_h = auth_headers(make_user("mod", UserRole.MAINTAINER))

        # Before tracking exists, nobody gets a token — not even a maintainer.
        assert client.get(url, headers=maintainer_h).json()[0]["tracking_token"] is None

        group = _generate(client, h, contribution["id"])
        for headers in (maintainer_h, admin_h):
            body = client.get(url, headers=headers).json()
            assert body[0]["tracking_token"] == group["tracking_token"]

        # The maker themselves is a regular user here: no token on this list
        # (they reach their own tracking from "My Contributions").
        assert client.get(url, headers=h).json()[0]["tracking_token"] is None
        # And the anonymous public read never carries it.
        assert client.get(url).json()[0]["tracking_token"] is None


class TestConfirmReceivedFromScan:
    """The center confirms receipt from the page it lands on after a scan."""

    def _tracked(
        self,
        client: TestClient,
        maker_h: dict[str, str],
        center_h: dict[str, str],
        admin_h: dict[str, str],
    ) -> dict[str, Any]:
        contribution = _setup_contribution(
            client, maker_h, admin_h, qty=2, center_h=center_h
        )
        # Left in `claimed`: the maker never tapped prepared or delivered,
        # which is exactly the case the scan-side button exists for.
        return _generate(client, maker_h, contribution["id"])

    def test_center_member_confirms_what_the_maker_never_advanced(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        center_owner_h = auth_headers(make_user("centro"))
        group = self._tracked(client, h, center_owner_h, admin_h)
        token = group["tracking_token"]

        # Only the center side is offered the button.
        assert client.get(f"{TRACK}/{token}").json()["can_mark_received"] is False
        assert (
            client.get(f"{TRACK}/{token}", headers=h).json()["can_mark_received"]
            is False
        )
        center_view = client.get(f"{TRACK}/{token}", headers=center_owner_h).json()
        assert center_view["can_mark_received"] is True
        assert center_view["contribution_status"] == "claimed"

        resp = client.post(f"{TRACK}/{token}/confirm-received", headers=center_owner_h)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["contribution_status"] == "received"
        # Done is done: the button is gone from the refreshed view.
        assert body["can_mark_received"] is False
        mine = client.get(f"{CONTRIB}/me", headers=h).json()[0]
        assert mine["status"] == "received"

    def test_item_token_receives_the_whole_contribution(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        # Receipt is a Contribution-level fact, so scanning any unit's QR
        # confirms the package, just as the group QR does.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        center_owner_h = auth_headers(make_user("centro2"))
        group = self._tracked(client, h, center_owner_h, admin_h)
        item_token = group["items"][1]["tracking_token"]
        resp = client.post(
            f"{TRACK}/{item_token}/confirm-received", headers=center_owner_h
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["contribution_status"] == "received"
        assert client.get(f"{CONTRIB}/me", headers=h).json()[0]["status"] == "received"

    def test_guests_and_strangers_cannot_confirm(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        center_owner_h = auth_headers(make_user("centro3"))
        group = self._tracked(client, h, center_owner_h, admin_h)
        token = group["tracking_token"]

        assert client.post(f"{TRACK}/{token}/confirm-received").status_code == 401
        # Holding the (public) token is not the same as being the receiver —
        # and neither is being the maker.
        for headers in (auth_headers(make_user("passerby")), h):
            resp = client.post(f"{TRACK}/{token}/confirm-received", headers=headers)
            assert resp.status_code == 403
            assert resp.json()["error"]["code"] == "NOT_RECEIVER"

    def test_maintainer_confirms_regardless_of_visibility(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        # Receipt authorization is the Contribution's, not the timeline's: a
        # maintainer confirms even a private tracking.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        maintainer_h = auth_headers(make_user("mod-receiver", UserRole.MAINTAINER))
        group = self._tracked(client, h, auth_headers(make_user("centro4")), admin_h)
        client.patch(
            f"{TRACKING}/groups/{group['group_id']}",
            headers=h,
            json={"visibility": "private"},
        )
        token = group["tracking_token"]
        resp = client.post(f"{TRACK}/{token}/confirm-received", headers=maintainer_h)
        assert resp.status_code == 200, resp.text
        assert resp.json()["contribution_status"] == "received"

    def test_no_button_without_a_drop_off_center(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        # A commitment made before picking a center has nowhere to be received.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        resource_id = client.post(
            RESOURCES,
            headers=h,
            json={"name": "Ferula", "source_url": "https://x.io/p.stl"},
        ).json()["id"]
        item_id = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "Campaign",
                "items": [{"resource_id": resource_id, "quantity": 5}],
            },
        ).json()["items"][0]["id"]
        contribution = client.post(
            CONTRIB, headers=h, json={"request_item_id": item_id, "quantity": 2}
        ).json()
        group = _generate(client, h, contribution["id"])
        token = group["tracking_token"]
        assert (
            client.get(f"{TRACK}/{token}", headers=admin_h).json()["can_mark_received"]
            is False
        )
        resp = client.post(f"{TRACK}/{token}/confirm-received", headers=admin_h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CENTER_REQUIRED"

    def test_unknown_token_404(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            f"{TRACK}/nope/confirm-received", headers=auth_headers(admin_user)
        )
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

    def test_captions_carry_the_group_unit_count(self):
        # The group code names the package size; each unit code says which of
        # that total it is, so a loose piece is still placeable.
        assert service.group_caption(20) == "Group · 20 items"
        assert service.group_caption(1) == "Group · 1 item"
        assert service.item_caption(1, 20) == "#1/20"
        assert service.item_caption(20, 20) == "#20/20"

    def test_bundle_captions_count_all_units_whatever_the_scope(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
        monkeypatch: Any,
    ):
        # Even when only the individual QRs are printed, each caption reports
        # the whole group's size — not how many QRs this download contains.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        group = _generate(client, h, contribution["id"])
        gid = group["group_id"]

        captured: list[list[tuple[str, str]]] = []
        original = qr.bundle_png_bytes

        def spy(labeled_urls: list[tuple[str, str]], *args: Any, **kw: Any) -> bytes:
            captured.append(labeled_urls)
            return original(labeled_urls, *args, **kw)

        monkeypatch.setattr(qr, "bundle_png_bytes", spy)

        both = client.get(f"{TRACKING}/groups/{gid}/qr-bundle.png", headers=h)
        assert both.status_code == 200
        assert [caption for caption, _ in captured[0]] == [
            "Group · 3 items",
            "#1/3",
            "#2/3",
            "#3/3",
        ]

        individual = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.png",
            params={"scope": "individual"},
            headers=h,
        )
        assert individual.status_code == 200
        assert [caption for caption, _ in captured[1]] == ["#1/3", "#2/3", "#3/3"]

    def test_group_caption_fits_the_printed_qr_width(self):
        # The caption is drawn on one unwrapped line, so the widest possible
        # one (the unit cap) must still fit inside a printed QR cell.
        widest = service.group_caption(500)
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        font = qr._font(round(3.5 * qr._MM))  # pyright: ignore[reportPrivateUsage]
        assert draw.textlength(widest, font=font) <= qr._PDF_QR  # pyright: ignore[reportPrivateUsage]

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


class TestReprintRange:
    """``seq_from``/``seq_to`` reprint only a window of the per-unit QRs."""

    def _spy(self, monkeypatch: Any) -> list[list[tuple[str, str]]]:
        captured: list[list[tuple[str, str]]] = []
        original = qr.bundle_png_bytes

        def spy(labeled_urls: list[tuple[str, str]], *args: Any, **kw: Any) -> bytes:
            captured.append(labeled_urls)
            return original(labeled_urls, *args, **kw)

        monkeypatch.setattr(qr, "bundle_png_bytes", spy)
        return captured

    def test_window_prints_only_those_units_with_full_group_captions(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
        monkeypatch: Any,
    ):
        """The 283→300 case: reprint 4-5 of a 5-unit group, captions say /5."""
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=5)
        group = _generate(client, h, contribution["id"])
        captured = self._spy(monkeypatch)

        resp = client.get(
            f"{TRACKING}/groups/{group['group_id']}/qr-bundle.png",
            params={"scope": "individual", "seq_from": 4, "seq_to": 5},
            headers=h,
        )
        assert resp.status_code == 200, resp.text
        # Only the missing labels, each still numbered against the whole group.
        assert [caption for caption, _ in captured[0]] == ["#4/5", "#5/5"]

    def test_open_ended_bounds(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
        monkeypatch: Any,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=4)
        group = _generate(client, h, contribution["id"])
        gid = group["group_id"]
        captured = self._spy(monkeypatch)

        # Only a lower bound: everything from there on.
        client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.png",
            params={"scope": "individual", "seq_from": 3},
            headers=h,
        )
        assert [c for c, _ in captured[0]] == ["#3/4", "#4/4"]

        # Only an upper bound: everything up to it.
        client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.png",
            params={"scope": "individual", "seq_to": 2},
            headers=h,
        )
        assert [c for c, _ in captured[1]] == ["#1/4", "#2/4"]

    def test_range_keeps_the_group_qr_when_scope_is_both(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
        monkeypatch: Any,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=4)
        group = _generate(client, h, contribution["id"])
        captured = self._spy(monkeypatch)

        client.get(
            f"{TRACKING}/groups/{group['group_id']}/qr-bundle.png",
            params={"seq_from": 3, "seq_to": 3},
            headers=h,
        )
        assert [c for c, _ in captured[0]] == ["Group · 4 items", "#3/4"]

    def test_group_only_scope_ignores_the_range(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        # There are no per-unit QRs to narrow, so an out-of-range window is
        # simply irrelevant rather than an error.
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=2)
        group = _generate(client, h, contribution["id"])
        resp = client.get(
            f"{TRACKING}/groups/{group['group_id']}/qr-bundle.png",
            params={"scope": "group", "seq_from": 50, "seq_to": 90},
            headers=h,
        )
        assert resp.status_code == 200

    def test_empty_window_is_rejected(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """A blank sheet would look like a successful print, so it 400s."""
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        gid = _generate(client, h, contribution["id"])["group_id"]

        beyond = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.pdf",
            params={"scope": "individual", "seq_from": 9, "seq_to": 12},
            headers=h,
        )
        assert beyond.status_code == 400
        assert beyond.json()["error"]["code"] == "INVALID_UNIT_RANGE"

        inverted = client.get(
            f"{TRACKING}/groups/{gid}/qr-bundle.pdf",
            params={"scope": "individual", "seq_from": 3, "seq_to": 1},
            headers=h,
        )
        assert inverted.status_code == 400

    def test_range_must_be_positive(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        gid = _generate(client, h, contribution["id"])["group_id"]
        assert (
            client.get(
                f"{TRACKING}/groups/{gid}/qr-bundle.png",
                params={"seq_from": 0},
                headers=h,
            ).status_code
            == 422
        )


class TestMaintainerQuantityCorrection:
    """``PATCH /track/{token}/quantity`` — the center corrects the real count."""

    def test_growing_from_the_scan_page_keeps_printed_labels(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """The headline case: maker committed 3, the box holds 5."""
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        group = _generate(client, h, contribution["id"])
        before = {i["sequence"]: i["tracking_token"] for i in group["items"]}

        resp = client.patch(
            f"{TRACK}/{group['tracking_token']}/quantity",
            headers=admin_h,
            json={"quantity": 5},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["quantity"] == 5
        assert resp.json()["tracked_units"] == 5

        after = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        assert [i["sequence"] for i in after["items"]] == [1, 2, 3, 4, 5]
        # Units 1-3 keep the tokens already printed on paper.
        for item in after["items"]:
            if item["sequence"] in before:
                assert item["tracking_token"] == before[item["sequence"]]

    def test_works_after_delivery_when_the_maker_edit_is_locked(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Exactly when the discrepancy surfaces: the package is already in."""
        center_owner = make_user("centerboss", UserRole.USER)
        center_h = auth_headers(center_owner)
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3, center_h=center_h)
        group = _generate(client, h, contribution["id"])
        cid = contribution["id"]
        client.post(f"{CONTRIB}/{cid}/mark-prepared", headers=h)
        client.post(f"{CONTRIB}/{cid}/mark-delivered", headers=h)

        # The maker's own edit is locked from `delivered` on...
        locked = client.patch(f"{CONTRIB}/{cid}", headers=h, json={"quantity": 5})
        assert locked.status_code == 409
        assert locked.json()["error"]["code"] == "CONTRIBUTION_LOCKED"

        # ...but the maintainer correction goes through.
        resp = client.patch(
            f"{TRACK}/{group['tracking_token']}/quantity",
            headers=admin_h,
            json={"quantity": 5},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["quantity"] == 5

    def test_shrinking_retires_units_for_good(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=4)
        group = _generate(client, h, contribution["id"])
        token = group["tracking_token"]
        unit4 = next(i for i in group["items"] if i["sequence"] == 4)

        shrunk = client.patch(
            f"{TRACK}/{token}/quantity", headers=admin_h, json={"quantity": 2}
        )
        assert shrunk.status_code == 200, shrunk.text
        assert shrunk.json()["tracked_units"] == 2
        assert client.get(f"{TRACK}/{unit4['tracking_token']}").status_code == 404

        # Growing back mints a new QR for unit 4; the old one stays dead.
        client.patch(f"{TRACK}/{token}/quantity", headers=admin_h, json={"quantity": 4})
        assert client.get(f"{TRACK}/{unit4['tracking_token']}").status_code == 404
        after = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        regrown = next(i for i in after["items"] if i["sequence"] == 4)
        assert regrown["tracking_token"] != unit4["tracking_token"]
        assert client.get(f"{TRACK}/{regrown['tracking_token']}").status_code == 200

    def test_shrink_from_a_retired_item_token_returns_the_group_view(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """The write succeeded, so it must not answer with that unit's 404."""
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=4)
        group = _generate(client, h, contribution["id"])
        unit4 = next(i for i in group["items"] if i["sequence"] == 4)

        resp = client.patch(
            f"{TRACK}/{unit4['tracking_token']}/quantity",
            headers=admin_h,
            json={"quantity": 2},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["target_kind"] == "group"
        assert body["tracking_token"] == group["tracking_token"]
        assert body["quantity"] == 2

    def test_maker_and_guests_are_refused(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """Holding the token is not a licence to rewrite the commitment."""
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        token = _generate(client, h, contribution["id"])["tracking_token"]

        # The maker owns the tracking but not this override.
        maker = client.patch(
            f"{TRACK}/{token}/quantity", headers=h, json={"quantity": 9}
        )
        assert maker.status_code == 403
        assert maker.json()["error"]["code"] == "NOT_THE_MAKER"
        assert (
            client.patch(f"{TRACK}/{token}/quantity", json={"quantity": 9}).status_code
            == 401
        )
        # Unchanged.
        assert client.get(f"{TRACK}/{token}").json()["quantity"] == 3

    def test_maintainer_may_correct(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        maintainer_h = auth_headers(make_user("mod", UserRole.MAINTAINER))
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        token = _generate(client, h, contribution["id"])["tracking_token"]
        resp = client.patch(
            f"{TRACK}/{token}/quantity", headers=maintainer_h, json={"quantity": 6}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["quantity"] == 6

    def test_rejects_a_non_positive_quantity(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        token = _generate(client, h, contribution["id"])["tracking_token"]
        assert (
            client.patch(
                f"{TRACK}/{token}/quantity", headers=admin_h, json={"quantity": 0}
            ).status_code
            == 422
        )

    def test_same_quantity_is_a_noop(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        group = _generate(client, h, contribution["id"])
        before = {i["sequence"]: i["tracking_token"] for i in group["items"]}
        resp = client.patch(
            f"{TRACK}/{group['tracking_token']}/quantity",
            headers=admin_h,
            json={"quantity": 3},
        )
        assert resp.status_code == 200, resp.text
        after = client.get(
            f"{TRACKING}/contributions/{contribution['id']}", headers=h
        ).json()
        assert {i["sequence"]: i["tracking_token"] for i in after["items"]} == before

    def test_unknown_token_is_404(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        assert (
            client.patch(
                f"{TRACK}/nope/quantity",
                headers=auth_headers(admin_user),
                json={"quantity": 2},
            ).status_code
            == 404
        )

    def test_can_manage_is_maintainer_only(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Drives the manage panel; the maker does not get the override."""
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(client, h, admin_h, qty=3)
        token = _generate(client, h, contribution["id"])["tracking_token"]

        assert client.get(f"{TRACK}/{token}").json()["can_manage"] is False
        assert client.get(f"{TRACK}/{token}", headers=h).json()["can_manage"] is False
        admin_view = client.get(f"{TRACK}/{token}", headers=admin_h).json()
        assert admin_view["can_manage"] is True
        assert admin_view["tracked_units"] == 3
        maintainer_h = auth_headers(make_user("mod2", UserRole.MAINTAINER))
        assert (
            client.get(f"{TRACK}/{token}", headers=maintainer_h).json()["can_manage"]
            is True
        )

    def test_resource_label_flag_is_manager_only(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h, admin_h = auth_headers(normal_user), auth_headers(admin_user)
        contribution = _setup_contribution(
            client, h, admin_h, qty=2, label_url="https://x.io/label.png"
        )
        token = _generate(client, h, contribution["id"])["tracking_token"]
        assert client.get(f"{TRACK}/{token}").json()["resource_has_label"] is False
        assert (
            client.get(f"{TRACK}/{token}", headers=admin_h).json()["resource_has_label"]
            is True
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
