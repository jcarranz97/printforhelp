"""Tests for the Request moderation gate (FR-134 / FR-135).

Every test here carries ``@pytest.mark.moderation`` so the auto-publish fixture
in ``conftest`` steps aside and the real draft-by-default behaviour applies.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.users.models import User

RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CONTRIB = "/api/v1/contributions"
COMMENTS = "/api/v1/comments"
ACTIVITY = "/api/v1/activity"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]

pytestmark = pytest.mark.moderation


def _resource(client: TestClient, h: dict[str, str]) -> str:
    return client.post(
        RESOURCES,
        headers=h,
        json={"name": "Ferula", "source_url": "https://x.io/p.stl"},
    ).json()["id"]


def _campaign(
    client: TestClient, h: dict[str, str], title: str = "C"
) -> dict[str, Any]:
    """Create a campaign with one item (the minimum a review needs)."""
    resource_id = _resource(client, h)
    resp = client.post(
        REQUESTS,
        headers=h,
        json={
            "title": title,
            "items": [{"resource_id": resource_id, "quantity": 5}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestDraftByDefault:
    def test_new_campaign_starts_as_draft(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        body = _campaign(client, auth_headers(normal_user))
        assert body["moderation_status"] == "draft"

    def test_maintainer_campaign_is_born_approved(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        maintainer = make_user("mod1", role="maintainer")
        body = _campaign(client, auth_headers(maintainer))
        assert body["moderation_status"] == "approved"
        # ...and is immediately public.
        titles = [r["title"] for r in client.get(REQUESTS).json()]
        assert body["title"] in titles


class TestVisibility:
    """A leaked link must be worthless to anyone but the author/maintainers."""

    def test_draft_hidden_from_public_list(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        _campaign(client, auth_headers(normal_user), title="Secret draft")
        titles = [r["title"] for r in client.get(REQUESTS).json()]
        assert "Secret draft" not in titles

    def test_author_sees_own_draft_in_list(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        _campaign(client, h, title="My draft")
        titles = [r["title"] for r in client.get(REQUESTS, headers=h).json()]
        assert "My draft" in titles

    def test_maintainer_sees_others_drafts_in_list(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _campaign(client, auth_headers(normal_user), title="Somebody's draft")
        mh = auth_headers(make_user("mod2", role="maintainer"))
        titles = [r["title"] for r in client.get(REQUESTS, headers=mh).json()]
        assert "Somebody's draft" in titles

    def test_leaked_link_404s_for_a_stranger(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        campaign = _campaign(client, auth_headers(normal_user))
        rid = campaign["id"]
        stranger = auth_headers(make_user("stranger"))

        # Guest and logged-in stranger alike: the campaign does not exist.
        assert client.get(f"{REQUESTS}/{rid}").status_code == 404
        assert client.get(f"{REQUESTS}/{rid}", headers=stranger).status_code == 404
        # ...nor do its items or their commitments.
        assert client.get(f"{REQUESTS}/{rid}/items/1").status_code == 404
        assert client.get(f"{REQUESTS}/{rid}/items/1/contributions").status_code == 404

    def test_author_and_maintainer_can_open_the_link(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        mh = auth_headers(make_user("mod3", role="maintainer"))
        assert client.get(f"{REQUESTS}/{rid}", headers=h).status_code == 200
        assert client.get(f"{REQUESTS}/{rid}", headers=mh).status_code == 200
        assert client.get(f"{REQUESTS}/{rid}/items/1", headers=h).status_code == 200

    def test_comments_and_activity_are_hidden_too(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The leaked link exposes the UUID, so the feeds must gate as well."""
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        stranger = auth_headers(make_user("nosy"))
        params = {"entity_type": "request", "entity_id": rid}

        assert client.get(COMMENTS, params=params, headers=stranger).json() == []
        assert client.get(ACTIVITY, params=params, headers=stranger).json() == []
        # ...and a stranger cannot post onto it either.
        resp = client.post(
            COMMENTS,
            headers=stranger,
            json={"entity_type": "request", "entity_id": rid, "body": "hi"},
        )
        assert resp.status_code >= 400

    def test_cannot_commit_to_an_unpublished_campaign(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Knowing an item id must not be enough to claim against a draft."""
        campaign = _campaign(client, auth_headers(normal_user))
        item_id = campaign["items"][0]["id"]
        maker = auth_headers(make_user("eager"))
        resp = client.post(
            CONTRIB,
            headers=maker,
            json={"request_item_id": item_id, "quantity": 2},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NOT_PUBLISHED"


class TestReviewFlow:
    def test_submit_approve_publishes(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h, title="Ferulas")["id"]
        mh = auth_headers(make_user("mod4", role="maintainer"))

        submitted = client.post(f"{REQUESTS}/{rid}/submit", headers=h)
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["moderation_status"] == "pending"
        # It shows up in the maintainer queue.
        queue = client.get(f"{REQUESTS}/review-queue", headers=mh).json()
        assert rid in [r["id"] for r in queue]
        # Still not public while it waits.
        assert client.get(f"{REQUESTS}/{rid}").status_code == 404

        approved = client.post(f"{REQUESTS}/{rid}/approve", headers=mh)
        assert approved.status_code == 200, approved.text
        assert approved.json()["moderation_status"] == "approved"
        assert client.get(f"{REQUESTS}/{rid}").status_code == 200
        assert "Ferulas" in [r["title"] for r in client.get(REQUESTS).json()]

    def test_submit_requires_an_item(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        rid = client.post(REQUESTS, headers=h, json={"title": "Empty"}).json()["id"]
        resp = client.post(f"{REQUESTS}/{rid}/submit", headers=h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NEEDS_ITEM"

    def test_asking_for_information_keeps_it_pending(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Needing more info is a question, not a verdict (FR-136).

        The reviewer asks in the private thread; the campaign stays ``pending``
        — in the queue they are working through — until they can actually
        decide. There is no ``request-changes`` transition any more.
        """
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        mh = auth_headers(make_user("mod5", role="maintainer"))
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)

        # The "ask for more information" transition no longer exists at all.
        assert (
            client.post(f"{REQUESTS}/{rid}/request-changes", headers=mh).status_code
            == 404
        )

        asked = _post_review_comment(client, rid, mh, "Who is this for?")
        assert asked.status_code == 201
        answered = _post_review_comment(client, rid, h, "Hogar Bambi.")
        assert answered.status_code == 201

        # Still pending, still in the queue, still not public.
        detail = client.get(f"{REQUESTS}/{rid}", headers=h).json()
        assert detail["moderation_status"] == "pending"
        assert rid in [
            r["id"] for r in client.get(f"{REQUESTS}/review-queue", headers=mh).json()
        ]
        assert client.get(f"{REQUESTS}/{rid}").status_code == 404

        # Once satisfied, the reviewer decides.
        approved = client.post(f"{REQUESTS}/{rid}/approve", headers=mh)
        assert approved.json()["moderation_status"] == "approved"

    def test_rejected_is_never_public_but_can_be_resubmitted(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        mh = auth_headers(make_user("mod6", role="maintainer"))
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)

        rejected = client.post(f"{REQUESTS}/{rid}/reject", headers=mh)
        assert rejected.json()["moderation_status"] == "rejected"
        assert client.get(f"{REQUESTS}/{rid}").status_code == 404
        # The author may still fix it and try again.
        assert (
            client.post(f"{REQUESTS}/{rid}/submit", headers=h).json()[
                "moderation_status"
            ]
            == "pending"
        )

    def test_only_maintainers_may_review(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)
        # Not even the author can approve their own campaign.
        assert client.post(f"{REQUESTS}/{rid}/approve", headers=h).status_code == 403
        assert client.get(f"{REQUESTS}/review-queue", headers=h).status_code == 403
        assert client.get(f"{REQUESTS}/review-queue").status_code == 401

    def test_cannot_review_something_not_pending(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]  # still a draft
        mh = auth_headers(make_user("mod7", role="maintainer"))
        resp = client.post(f"{REQUESTS}/{rid}/approve", headers=mh)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NOT_PENDING"

    def test_submit_requires_the_requester(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        rid = _campaign(client, auth_headers(normal_user))["id"]
        stranger = auth_headers(make_user("hijacker"))
        resp = client.post(f"{REQUESTS}/{rid}/submit", headers=stranger)
        assert resp.status_code == 403


class TestUnpublish:
    """FR-135: a live campaign can be pulled back down for review."""

    def _published(
        self,
        client: TestClient,
        author_h: dict[str, str],
        maintainer_h: dict[str, str],
    ) -> str:
        rid = _campaign(client, author_h, title="Live")["id"]
        client.post(f"{REQUESTS}/{rid}/submit", headers=author_h)
        client.post(f"{REQUESTS}/{rid}/approve", headers=maintainer_h)
        return rid

    def test_maintainer_takes_a_live_campaign_down(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        mh = auth_headers(make_user("mod8", role="maintainer"))
        rid = self._published(client, h, mh)
        assert client.get(f"{REQUESTS}/{rid}").status_code == 200

        pulled = client.post(f"{REQUESTS}/{rid}/unpublish", headers=mh)
        assert pulled.status_code == 200, pulled.text
        assert pulled.json()["moderation_status"] == "pending"
        # Gone from public reads immediately, and back in the queue.
        assert client.get(f"{REQUESTS}/{rid}").status_code == 404
        assert "Live" not in [r["title"] for r in client.get(REQUESTS).json()]
        assert rid in [
            r["id"] for r in client.get(f"{REQUESTS}/review-queue", headers=mh).json()
        ]
        # ...and can be put back up.
        client.post(f"{REQUESTS}/{rid}/approve", headers=mh)
        assert client.get(f"{REQUESTS}/{rid}").status_code == 200

    def test_author_may_pull_their_own_campaign_down(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        mh = auth_headers(make_user("mod9", role="maintainer"))
        rid = self._published(client, h, mh)
        assert client.post(f"{REQUESTS}/{rid}/unpublish", headers=h).status_code == 200
        assert client.get(f"{REQUESTS}/{rid}").status_code == 404

    def test_a_stranger_cannot_take_a_campaign_down(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        mh = auth_headers(make_user("mod10", role="maintainer"))
        rid = self._published(client, h, mh)
        stranger = auth_headers(make_user("vandal"))
        resp = client.post(f"{REQUESTS}/{rid}/unpublish", headers=stranger)
        assert resp.status_code == 403
        assert client.get(f"{REQUESTS}/{rid}").status_code == 200

    def test_cannot_unpublish_something_not_published(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]  # still a draft
        mh = auth_headers(make_user("mod11", role="maintainer"))
        resp = client.post(f"{REQUESTS}/{rid}/unpublish", headers=mh)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_NOT_APPROVED"


REVIEW = {"entity_type": "request_review"}


def _review_params(request_id: str) -> dict[str, str]:
    return {"entity_type": "request_review", "entity_id": request_id}


def _post_review_comment(
    client: TestClient, request_id: str, h: dict[str, str], body: str
):
    return client.post(
        COMMENTS,
        headers=h,
        json={"entity_type": "request_review", "entity_id": request_id, "body": body},
    )


class TestReviewThread:
    """The review is a conversation on its OWN, permanently private timeline.

    Separate from the campaign's public comments: publishing a campaign must
    never publish the conversation that vetted it.
    """

    def test_verdicts_land_on_the_review_timeline(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        mh = auth_headers(make_user("mod14", role="maintainer"))
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)
        # A verdict with no note at all — the reasoning goes in the thread.
        resp = client.post(f"{REQUESTS}/{rid}/reject", headers=mh)
        assert resp.status_code == 200, resp.text
        assert resp.json()["moderation_status"] == "rejected"

        feed = client.get(ACTIVITY, params=_review_params(rid), headers=h).json()
        moves = [
            e["changes"]["moderation"] for e in feed if "moderation" in e["changes"]
        ]
        assert {"from": "pending", "to": "rejected"} in moves
        assert {"from": "draft", "to": "pending"} in moves

        # ...and NOT on the campaign's public timeline.
        public = client.get(
            ACTIVITY,
            params={"entity_type": "request", "entity_id": rid},
            headers=h,
        ).json()
        assert not [e for e in public if "moderation" in e["changes"]]

    def test_author_and_reviewer_can_talk_nobody_else(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        mh = auth_headers(make_user("mod15", role="maintainer"))
        stranger = auth_headers(make_user("lurker"))

        assert _post_review_comment(
            client, rid, mh, "Who is this for?"
        ).status_code == (201)
        assert _post_review_comment(client, rid, h, "Hogar Bambi.").status_code == 201

        params = _review_params(rid)
        assert len(client.get(COMMENTS, params=params, headers=h).json()) == 2
        assert len(client.get(COMMENTS, params=params, headers=mh).json()) == 2
        # A stranger — and a guest — see nothing and cannot join in.
        assert client.get(COMMENTS, params=params, headers=stranger).json() == []
        assert client.get(COMMENTS, params=params).json() == []
        assert _post_review_comment(client, rid, stranger, "hi").status_code >= 400

    def test_review_thread_stays_private_after_publication(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The whole point: approving the campaign must not expose the review."""
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        mh = auth_headers(make_user("mod16", role="maintainer"))
        stranger = auth_headers(make_user("passerby"))

        _post_review_comment(client, rid, mh, "Is this beneficiary real?")
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)
        client.post(f"{REQUESTS}/{rid}/approve", headers=mh)

        # The campaign is now public...
        assert client.get(f"{REQUESTS}/{rid}").status_code == 200
        # ...but its review conversation is still invisible to everyone else.
        params = _review_params(rid)
        assert client.get(COMMENTS, params=params).json() == []
        assert client.get(COMMENTS, params=params, headers=stranger).json() == []
        assert client.get(ACTIVITY, params=params, headers=stranger).json() == []
        assert _post_review_comment(client, rid, stranger, "nosy").status_code >= 400
        # The participants still have it.
        assert len(client.get(COMMENTS, params=params, headers=h).json()) == 1

    def test_public_comments_stay_public_and_separate(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """The two threads never bleed into each other."""
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        mh = auth_headers(make_user("mod17", role="maintainer"))
        _post_review_comment(client, rid, mh, "internal: check the org")
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)
        client.post(f"{REQUESTS}/{rid}/approve", headers=mh)
        client.post(
            COMMENTS,
            headers=h,
            json={"entity_type": "request", "entity_id": rid, "body": "Thanks all!"},
        )

        public = client.get(
            COMMENTS, params={"entity_type": "request", "entity_id": rid}
        ).json()
        bodies = [c["body"] for c in public]
        assert bodies == ["Thanks all!"]
        assert "internal: check the org" not in bodies

    def test_a_stranger_cannot_watch_the_review_thread(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        """Subscribing would otherwise leak that a conversation is happening."""
        h = auth_headers(normal_user)
        rid = _campaign(client, h)["id"]
        stranger = auth_headers(make_user("subscriber"))
        resp = client.post(
            "/api/v1/watches",
            headers=stranger,
            json={"entity_type": "request_review", "entity_id": rid},
        )
        assert resp.status_code >= 400
        # The author may.
        assert (
            client.post(
                "/api/v1/watches",
                headers=h,
                json={"entity_type": "request_review", "entity_id": rid},
            ).status_code
            < 400
        )


class TestNotifications:
    def test_submitting_pings_the_maintainers(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        maintainer = make_user("mod12", role="maintainer")
        mh = auth_headers(maintainer)
        rid = _campaign(client, h)["id"]
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)

        notes = client.get("/api/v1/notifications", headers=mh).json()
        events = [n["event"] for n in notes]
        assert "request_submitted" in events

    def test_the_verdict_pings_the_author(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        mh = auth_headers(make_user("mod13", role="maintainer"))
        rid = _campaign(client, h)["id"]
        client.post(f"{REQUESTS}/{rid}/submit", headers=h)
        client.post(f"{REQUESTS}/{rid}/approve", headers=mh)

        notes = client.get("/api/v1/notifications", headers=h).json()
        assert "request_reviewed" in [n["event"] for n in notes]
