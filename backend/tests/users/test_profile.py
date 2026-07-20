"""Tests for the self-profile editor and the public profile page.

Covers ``PUT /users/me`` (name/bio), ``PUT /users/me/avatar`` (picture + crop),
and the public, unauthenticated ``GET /users/{username}/profile`` (identity +
the contribution activity timeline), including the email-never-leaked and
moderation-gate guarantees.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contributions.models import Contribution
from app.requests.constants import ModerationStatus
from app.requests.models import Request
from app.users.constants import UserRole
from app.users.models import User, UsernameChange

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
        assert body["activity"]["months"] == []
        assert body["contributions_total"] == 0

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

    def test_timeline_shows_a_claim(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        _, item_id, center_id = _setup_item(client, h, auth_headers(admin_user))
        _claim(client, h, item_id, center_id)

        body = client.get(f"{USERS}/user1/profile").json()
        assert body["contributions_total"] == 1
        assert len(body["activity"]["months"]) == 1
        assert body["activity"]["months"][0]["contributions_count"] == 1
        entries = body["activity"]["months"][0]["entries"]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["kind"] == "claimed"
        assert entry["total_quantity"] == 4
        assert entry["request_count"] == 1
        # One campaign, so the summary can name it instead of counting.
        assert entry["single_request_title"] == "Splints for Venezuela"
        # Every stage carries its per-project breakdown, not just printing.
        assert [(i["resource_name"], i["quantity"]) for i in entry["items"]] == [
            ("Ferula", 4)
        ]

    def test_released_commitments_leave_the_timeline(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """Releasing hands the units back, so it must not keep counting.

        Releasing only flips ``status`` — the row stays active as history — so
        a filter on ``active`` alone would leave the original claim counted for
        ever (claims increment, releases never decrement).
        """
        h = auth_headers(normal_user)
        _, item_id, center_id = _setup_item(client, h, auth_headers(admin_user))
        kept = _claim(client, h, item_id, center_id)
        released = _claim(client, h, item_id, center_id)

        before = client.get(f"{USERS}/user1/profile").json()
        assert before["contributions_total"] == 2
        assert before["activity"]["months"][0]["entries"][0]["total_quantity"] == 8

        resp = client.post(f"{CONTRIB}/{released['id']}/release", headers=h)
        assert resp.status_code == 200, resp.text

        after = client.get(f"{USERS}/user1/profile").json()
        assert after["contributions_total"] == 1
        entries = after["activity"]["months"][0]["entries"]
        assert len(entries) == 1
        assert entries[0]["kind"] == "claimed"
        # Only the commitment that is still standing.
        assert entries[0]["total_quantity"] == 4

        # Releasing the last one empties the timeline entirely.
        client.post(f"{CONTRIB}/{kept['id']}/release", headers=h)
        empty = client.get(f"{USERS}/user1/profile").json()
        assert empty["contributions_total"] == 0
        assert empty["activity"]["months"] == []

    def test_timeline_groups_prints_and_breaks_them_down(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """Two prints in the same month roll into one entry, largest first."""
        h = auth_headers(normal_user)
        admin_h = auth_headers(admin_user)
        _, item_a, center_id = _setup_item(client, h, admin_h)
        resource_b = client.post(
            RESOURCES,
            headers=h,
            json={"name": "Silbato", "source_url": "https://x.io/w.stl"},
        ).json()["id"]
        item_b = client.post(
            REQUESTS,
            headers=h,
            json={
                "title": "Whistles",
                "items": [{"resource_id": resource_b, "quantity": 50}],
            },
        ).json()["items"][0]["id"]

        small = _claim(client, h, item_a, center_id)  # quantity 4
        big = client.post(
            CONTRIB,
            headers=h,
            json={
                "request_item_id": item_b,
                "collection_center_id": center_id,
                "quantity": 30,
            },
        ).json()
        for contribution in (small, big):
            resp = client.post(
                f"{CONTRIB}/{contribution['id']}/mark-prepared", headers=h
            )
            assert resp.status_code == 200, resp.text

        body = client.get(f"{USERS}/user1/profile").json()
        entries = {e["kind"]: e for e in body["activity"]["months"][0]["entries"]}
        printed = entries["prepared"]
        assert printed["total_quantity"] == 34
        assert printed["request_count"] == 2
        # Spans two campaigns, so it counts rather than naming one.
        assert printed["single_request_title"] is None
        assert [item["resource_name"] for item in printed["items"]] == [
            "Silbato",
            "Ferula",
        ]
        assert [item["quantity"] for item in printed["items"]] == [30, 4]
        # The claims stay in the history alongside the prints...
        assert entries["claimed"]["total_quantity"] == 34
        # ...but the month counts two commitments, not four.
        assert body["activity"]["months"][0]["contributions_count"] == 2

    def test_advancing_keeps_the_earlier_stages_as_history(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        """Stages accumulate, but the month's counter stays deduplicated.

        The timeline is a history: printing a commitment must not erase the
        month in which it was claimed. The stage lines therefore overlap, while
        ``contributions_count`` still reports one commitment, not three.
        """
        h = auth_headers(normal_user)
        _, item_id, center_id = _setup_item(client, h, auth_headers(admin_user))
        contribution = _claim(client, h, item_id, center_id)  # quantity 4

        def snapshot() -> tuple[dict[str, int], int, int]:
            body = client.get(f"{USERS}/user1/profile").json()
            stages = {
                e["kind"]: e["total_quantity"]
                for month in body["activity"]["months"]
                for e in month["entries"]
            }
            month_count = body["activity"]["months"][0]["contributions_count"]
            return stages, month_count, body["contributions_total"]

        assert snapshot() == ({"claimed": 4}, 1, 1)

        client.post(f"{CONTRIB}/{contribution['id']}/mark-prepared", headers=h)
        assert snapshot() == ({"claimed": 4, "prepared": 4}, 1, 1)

        client.post(f"{CONTRIB}/{contribution['id']}/mark-delivered", headers=h)
        assert snapshot() == (
            {"claimed": 4, "prepared": 4, "delivered": 4},
            1,
            1,
        )

    def test_activity_pages_back_through_history(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        """Paging walks months with activity, never splitting or repeating one.

        Months are backdated directly: the API always stamps "now", and the
        point of the cursor is precisely to reach months the first page omits.
        """
        h = auth_headers(normal_user)
        _, item_id, center_id = _setup_item(client, h, auth_headers(admin_user))
        made = [_claim(client, h, item_id, center_id) for _ in range(4)]

        # One commitment per month, four months back, newest first.
        now = datetime.now(UTC)
        for offset, contribution in enumerate(made):
            row = db.query(Contribution).filter(
                Contribution.id == UUID(contribution["id"])
            )
            claimed = (now - timedelta(days=31 * offset)).replace(day=15)
            row.update({"claimed_at": claimed})
        db.commit()

        page = client.get(f"{USERS}/user1/profile").json()["activity"]
        seen: list[tuple[int, int]] = []
        pages = 0
        while True:
            pages += 1
            seen.extend((m["year"], m["month"]) for m in page["months"])
            # Default page size is two months of activity.
            assert len(page["months"]) <= 2
            if not page["has_more"]:
                assert page["next_before"] is None
                break
            resp = client.get(
                f"{USERS}/user1/activity", params={"before": page["next_before"]}
            )
            assert resp.status_code == 200, resp.text
            page = resp.json()

        assert pages == 2
        assert len(seen) == 4
        # Every month appears once, newest first.
        assert len(set(seen)) == 4
        assert seen == sorted(seen, reverse=True)

    def test_year_filter_scopes_calendar_and_timeline(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        """Selecting a year bounds the headline, the calendar and the timeline."""
        h = auth_headers(normal_user)
        _, item_id, center_id = _setup_item(client, h, auth_headers(admin_user))
        this_year = datetime.now(UTC).year
        # Two commitments: one stays in the current year, one is backdated.
        _claim(client, h, item_id, center_id)
        older = _claim(client, h, item_id, center_id)

        # Push one commitment into the previous calendar year (its last day, so
        # it stays as close as possible to the rolling 12-month window).
        db.query(Contribution).filter(Contribution.id == UUID(older["id"])).update(
            {"claimed_at": datetime(this_year - 1, 12, 31, tzinfo=UTC)}
        )
        db.commit()

        body = client.get(f"{USERS}/user1/profile", params={"year": this_year}).json()
        assert body["selected_year"] == this_year
        assert body["contributions_total"] == 1
        assert {d["date"][:4] for d in body["contribution_days"]} == {str(this_year)}
        assert {m["year"] for m in body["activity"]["months"]} == {this_year}

        previous = client.get(
            f"{USERS}/user1/profile", params={"year": this_year - 1}
        ).json()
        assert previous["contributions_total"] == 1
        assert {d["date"][:4] for d in previous["contribution_days"]} == {
            str(this_year - 1)
        }
        assert {m["year"] for m in previous["activity"]["months"]} == {this_year - 1}

        # Both years are offered, newest first.
        assert previous["available_years"][:2] == [this_year, this_year - 1]
        # The default view is a *rolling* 12 months rather than a calendar
        # year, so its count is not simply the sum of the two years — how much
        # of last year it reaches depends on today's date.
        default = client.get(f"{USERS}/user1/profile").json()
        assert default["selected_year"] is None
        assert default["contributions_total"] >= 1

        # A year with nothing in it is empty rather than an error.
        empty = client.get(f"{USERS}/user1/profile", params={"year": 2001}).json()
        assert empty["contributions_total"] == 0
        assert empty["contribution_days"] == []
        assert empty["activity"]["months"] == []

    def test_activity_endpoint_is_public_and_404s_for_unknown_user(
        self, client: TestClient, normal_user: User
    ):
        assert client.get(f"{USERS}/user1/activity").status_code == 200
        assert client.get(f"{USERS}/nobody/activity").status_code == 404

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
        published = client.get(f"{USERS}/user1/profile").json()
        assert published["contributions_total"] == 1
        assert published["activity"]["months"] != []

        # Pull it back to pending: it must vanish from the public profile.
        request.moderation_status = ModerationStatus.PENDING
        db.commit()
        unpublished = client.get(f"{USERS}/user1/profile").json()
        assert unpublished["contributions_total"] == 0
        assert unpublished["activity"]["months"] == []


def _rename(client: TestClient, h: dict[str, str], new_username: str) -> None:
    """Rename the caller's handle via the self endpoint; assert success."""
    resp = client.put(
        f"{USERS}/me/username", headers=h, json={"username": new_username}
    )
    assert resp.status_code == 200, resp.text


def _rename_entry(activity: dict[str, Any]) -> dict[str, Any] | None:
    """The single ``renamed`` entry on a timeline, or None if hidden away."""
    renames = [
        entry
        for month in activity["months"]
        for entry in month["entries"]
        if entry["kind"] == "renamed"
    ]
    assert len(renames) <= 1
    return renames[0] if renames else None


class TestHideUsernameChange:
    """The moderator control that hides a rename from the public timeline.

    A user who renamed away from an email-as-handle should not have the old
    email exposed for ever; a maintainer/admin can hide that rename so only
    they still see it (with the option to reveal it again).
    """

    VISIBILITY = f"{USERS}/username-changes"

    def test_rename_shows_publicly_without_the_id(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        _rename(client, auth_headers(normal_user), "renamed")
        activity = client.get(f"{USERS}/renamed/profile").json()["activity"]
        entry = _rename_entry(activity)
        assert entry is not None
        assert (entry["renamed_from"], entry["renamed_to"]) == ("user1", "renamed")
        # A regular/anonymous viewer never gets the change id or hidden flag.
        assert entry["rename_id"] is None
        assert entry["rename_hidden"] is False

    def test_maintainer_sees_the_rename_id(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _rename(client, auth_headers(normal_user), "renamed")
        mod = make_user("mod", UserRole.MAINTAINER)
        activity = client.get(
            f"{USERS}/renamed/profile", headers=auth_headers(mod)
        ).json()["activity"]
        entry = _rename_entry(activity)
        assert entry is not None
        assert entry["rename_id"] is not None
        assert entry["rename_hidden"] is False

    def _rename_and_id(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        auth_headers: AuthHeaders,
    ) -> str:
        _rename(client, auth_headers(normal_user), "renamed")
        change = (
            db.query(UsernameChange)
            .filter(UsernameChange.user_id == normal_user.id)
            .one()
        )
        return str(change.id)

    def test_hiding_removes_it_from_public_but_not_from_moderators(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        change_id = self._rename_and_id(client, db, normal_user, auth_headers)
        mod = make_user("mod", UserRole.MAINTAINER)

        resp = client.put(
            f"{self.VISIBILITY}/{change_id}/visibility",
            headers=auth_headers(mod),
            json={"hidden": True},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"id": change_id, "hidden": True}

        # Gone for the public...
        public = client.get(f"{USERS}/renamed/profile").json()["activity"]
        assert _rename_entry(public) is None

        # ...but the moderator still sees it, flagged as hidden.
        moderated = client.get(
            f"{USERS}/renamed/profile", headers=auth_headers(mod)
        ).json()["activity"]
        entry = _rename_entry(moderated)
        assert entry is not None
        assert entry["rename_hidden"] is True

    def test_hidden_rename_also_gone_from_the_activity_paging_endpoint(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        change_id = self._rename_and_id(client, db, normal_user, auth_headers)
        mod = make_user("mod", UserRole.MAINTAINER)
        client.put(
            f"{self.VISIBILITY}/{change_id}/visibility",
            headers=auth_headers(mod),
            json={"hidden": True},
        )
        public = client.get(f"{USERS}/renamed/activity").json()
        assert _rename_entry(public) is None
        moderated = client.get(
            f"{USERS}/renamed/activity", headers=auth_headers(mod)
        ).json()
        assert _rename_entry(moderated) is not None

    def test_unhiding_restores_it_publicly(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        change_id = self._rename_and_id(client, db, normal_user, auth_headers)
        mod_h = auth_headers(make_user("mod", UserRole.MAINTAINER))
        url = f"{self.VISIBILITY}/{change_id}/visibility"

        client.put(url, headers=mod_h, json={"hidden": True})
        hidden = client.get(f"{USERS}/renamed/profile").json()["activity"]
        assert _rename_entry(hidden) is None
        # Now reveal it again.
        resp = client.put(url, headers=mod_h, json={"hidden": False})
        assert resp.status_code == 200
        restored = client.get(f"{USERS}/renamed/profile").json()["activity"]
        assert _rename_entry(restored) is not None

    def test_hiding_leaves_the_rename_cooldown_intact(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        """Hiding must not soft-delete the row: the cooldown reads ``active``."""
        change_id = self._rename_and_id(client, db, normal_user, auth_headers)
        mod_h = auth_headers(make_user("mod", UserRole.MAINTAINER))
        client.put(
            f"{self.VISIBILITY}/{change_id}/visibility",
            headers=mod_h,
            json={"hidden": True},
        )
        # A second rename is still blocked by the cooldown that the hidden row
        # anchors — hiding changed visibility, not history.
        resp = client.put(
            f"{USERS}/me/username",
            headers=auth_headers(normal_user),
            json={"username": "again"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_CHANGE_TOO_SOON"

    def test_toggle_is_idempotent(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        change_id = self._rename_and_id(client, db, normal_user, auth_headers)
        mod_h = auth_headers(make_user("mod", UserRole.MAINTAINER))
        url = f"{self.VISIBILITY}/{change_id}/visibility"
        first = client.put(url, headers=mod_h, json={"hidden": True})
        second = client.put(url, headers=mod_h, json={"hidden": True})
        assert first.status_code == second.status_code == 200
        assert second.json() == {"id": change_id, "hidden": True}

    def test_regular_user_cannot_hide(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        change_id = self._rename_and_id(client, db, normal_user, auth_headers)
        # Even the owner of the rename is a regular user: forbidden.
        resp = client.put(
            f"{self.VISIBILITY}/{change_id}/visibility",
            headers=auth_headers(normal_user),
            json={"hidden": True},
        )
        assert resp.status_code == 403

    def test_anonymous_cannot_hide(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
        db: Session,
    ):
        change_id = self._rename_and_id(client, db, normal_user, auth_headers)
        resp = client.put(
            f"{self.VISIBILITY}/{change_id}/visibility",
            json={"hidden": True},
        )
        assert resp.status_code == 401

    def test_unknown_change_404(
        self,
        client: TestClient,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        mod_h = auth_headers(make_user("mod", UserRole.MAINTAINER))
        resp = client.put(
            f"{self.VISIBILITY}/00000000-0000-0000-0000-000000000000/visibility",
            headers=mod_h,
            json={"hidden": True},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "USERNAME_CHANGE_NOT_FOUND"
