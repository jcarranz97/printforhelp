"""Tests for polymorphic reactions ("likes") and their notifications."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.notifications import models as notif_models
from app.notifications.constants import NotificationCategory
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
COMMENTS = "/api/v1/comments"
REACTIONS = "/api/v1/reactions"
NOTIFICATIONS = "/api/v1/notifications"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _create_resource(client: TestClient, headers: dict[str, str]) -> dict:
    resp = client.post(
        RESOURCES,
        headers=headers,
        json={"name": "Ferula", "source_url": "https://example.com/p.stl"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_center(client: TestClient, headers: dict[str, str]) -> dict:
    resp = client.post(
        CENTERS,
        headers=headers,
        json={
            "name": "UCAB Lab",
            "address": "Av. Teheran, Caracas",
            "country": "VE",
            "city": "Caracas",
            "contact": "+58-212-407-4400",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_shipment(
    client: TestClient, center_id: str, headers: dict[str, str]
) -> dict:
    resp = client.post(
        f"{CENTERS}/{center_id}/shipments",
        headers=headers,
        json={"shipment_date": "2026-07-15", "status": "receiving"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_request(client: TestClient, headers: dict[str, str]) -> dict:
    resource = _create_resource(client, headers)
    resp = client.post(
        REQUESTS,
        headers=headers,
        json={"title": "Ferulas for VE", "items": [{"resource_id": resource["id"]}]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _post_comment(
    client: TestClient,
    headers: dict[str, str],
    entity_type: str,
    entity_id: str,
    body: str = "Hola",
) -> dict:
    resp = client.post(
        COMMENTS,
        headers=headers,
        json={"entity_type": entity_type, "entity_id": entity_id, "body": body},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _react(
    client: TestClient, headers: dict[str, str], entity_type: str, entity_id: str
) -> dict:
    resp = client.post(
        REACTIONS,
        headers=headers,
        json={"entity_type": entity_type, "entity_id": entity_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _state(
    client: TestClient,
    entity_type: str,
    entity_ids: list[str],
    headers: dict[str, str] | None = None,
) -> list[dict]:
    resp = client.get(
        REACTIONS,
        headers=headers or {},
        params={"entity_type": entity_type, "entity_id": entity_ids},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _reaction_notifications(client: TestClient, headers: dict[str, str]) -> list[dict]:
    resp = client.get(NOTIFICATIONS, headers=headers)
    assert resp.status_code == 200, resp.text
    return [n for n in resp.json() if n["event"] == "reaction"]


# --------------------------------------------------------------------------
# Core react / unreact / read
# --------------------------------------------------------------------------


class TestReactEndpoints:
    def test_react_idempotent_then_unreact(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("owner")
        resource = _create_resource(client, auth_headers(owner))
        rid = resource["id"]
        reactor = auth_headers(normal_user)

        first = _react(client, reactor, "resource", rid)
        assert first["count"] == 1
        assert first["reacted"] is True

        # Re-reacting is a no-op (still one like, still reacted).
        again = _react(client, reactor, "resource", rid)
        assert again["count"] == 1
        assert again["reacted"] is True

        removed = client.delete(f"{REACTIONS}/resource/{rid}", headers=reactor)
        assert removed.status_code == 200, removed.text
        assert removed.json() == {
            "entity_type": "resource",
            "entity_id": rid,
            "count": 0,
            "reacted": False,
        }

        # Unreacting again is a harmless no-op.
        removed_again = client.delete(f"{REACTIONS}/resource/{rid}", headers=reactor)
        assert removed_again.status_code == 200
        assert removed_again.json()["count"] == 0

    def test_re_react_after_unreact_reuses_row(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("owner")
        resource = _create_resource(client, auth_headers(owner))
        rid = resource["id"]
        reactor = auth_headers(normal_user)

        _react(client, reactor, "resource", rid)
        client.delete(f"{REACTIONS}/resource/{rid}", headers=reactor)
        restored = _react(client, reactor, "resource", rid)
        assert restored["count"] == 1
        assert restored["reacted"] is True

    def test_count_is_public_and_reacted_is_per_viewer(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("owner")
        other = make_user("other")
        resource = _create_resource(client, auth_headers(owner))
        rid = resource["id"]

        _react(client, auth_headers(normal_user), "resource", rid)
        _react(client, auth_headers(other), "resource", rid)

        # Anonymous read: count visible, reacted always false.
        anon = _state(client, "resource", [rid])[0]
        assert anon["count"] == 2
        assert anon["reacted"] is False

        # A third user sees the count but has not reacted.
        third = make_user("third")
        seen = _state(client, "resource", [rid], auth_headers(third))[0]
        assert seen["count"] == 2
        assert seen["reacted"] is False

        # The owner reacted view.
        mine = _state(client, "resource", [rid], auth_headers(normal_user))[0]
        assert mine["reacted"] is True

    def test_batch_state_for_comments(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        ah = auth_headers(author)
        resource = _create_resource(client, ah)
        c1 = _post_comment(client, ah, "resource", resource["id"], "one")
        c2 = _post_comment(client, ah, "resource", resource["id"], "two")

        _react(client, auth_headers(normal_user), "comment", c1["id"])

        states = _state(
            client, "comment", [c1["id"], c2["id"]], auth_headers(normal_user)
        )
        by_id = {s["entity_id"]: s for s in states}
        assert by_id[c1["id"]] == {
            "entity_type": "comment",
            "entity_id": c1["id"],
            "count": 1,
            "reacted": True,
        }
        assert by_id[c2["id"]]["count"] == 0
        assert by_id[c2["id"]]["reacted"] is False


# --------------------------------------------------------------------------
# Validation & auth
# --------------------------------------------------------------------------


class TestReactionValidation:
    def test_react_requires_auth(self, client: TestClient):
        resp = client.post(
            REACTIONS,
            json={
                "entity_type": "resource",
                "entity_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert resp.status_code == 401

    def test_unreact_requires_auth(self, client: TestClient):
        resp = client.delete(
            f"{REACTIONS}/resource/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 401

    def test_react_to_missing_entity_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            REACTIONS,
            headers=auth_headers(normal_user),
            json={
                "entity_type": "resource",
                "entity_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "INVALID_REACTION_TARGET"

    def test_react_to_non_reactable_type_is_404(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        # The private review thread is commentable but not reactable.
        request = _create_request(client, auth_headers(make_user("owner")))
        resp = client.post(
            REACTIONS,
            headers=auth_headers(normal_user),
            json={"entity_type": "request_review", "entity_id": request["id"]},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "INVALID_REACTION_TARGET"

    def test_state_of_non_reactable_type_is_masked(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        rid = "00000000-0000-0000-0000-000000000000"
        state = _state(client, "tracking_group", [rid], auth_headers(normal_user))[0]
        assert state["count"] == 0
        assert state["reacted"] is False


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------


class TestReactionNotifications:
    def test_reacting_notifies_resource_owner(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("owner")
        resource = _create_resource(client, auth_headers(owner))

        _react(client, auth_headers(normal_user), "resource", resource["id"])

        notes = _reaction_notifications(client, auth_headers(owner))
        assert len(notes) == 1
        assert notes[0]["actor"]["username"] == normal_user.username
        assert notes[0]["link"] == f"/parts/{resource['id']}"
        assert notes[0]["entity_type"] == "resource"

    def test_reacting_to_comment_notifies_author_with_anchor(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("cauthor")
        ah = auth_headers(author)
        resource = _create_resource(client, ah)
        comment = _post_comment(client, ah, "resource", resource["id"], "nice work")

        _react(client, auth_headers(normal_user), "comment", comment["id"])

        notes = _reaction_notifications(client, ah)
        assert len(notes) == 1
        note = notes[0]
        assert note["entity_type"] == "comment"
        assert note["comment_id"] == comment["id"]
        # Deep-links to the parent page and scrolls to the comment.
        assert note["link"] == f"/parts/{resource['id']}"
        assert note["anchor"] == f"comment-{comment['id']}"

    def test_reacting_to_request_notifies_requester(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("reqowner")
        request = _create_request(client, auth_headers(owner))

        _react(client, auth_headers(normal_user), "request", request["id"])
        _react(
            client,
            auth_headers(normal_user),
            "request_item",
            request["items"][0]["id"],
        )

        notes = _reaction_notifications(client, auth_headers(owner))
        assert {n["entity_type"] for n in notes} == {"request", "request_item"}

    def test_reacting_to_center_and_shipment_notifies_owner(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("ccowner")
        oh = auth_headers(owner)
        center = _create_center(client, oh)
        shipment = _create_shipment(client, center["id"], oh)

        _react(client, auth_headers(normal_user), "collection_center", center["id"])
        _react(client, auth_headers(normal_user), "shipment", shipment["id"])

        notes = _reaction_notifications(client, oh)
        assert {n["entity_type"] for n in notes} == {"collection_center", "shipment"}

    def test_self_reaction_does_not_notify(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        _react(client, auth_headers(normal_user), "resource", resource["id"])
        assert _reaction_notifications(client, auth_headers(normal_user)) == []

    def test_in_app_reaction_pref_off_suppresses_notification(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("owner")
        oh = auth_headers(owner)
        # Owner turns the reaction category fully off.
        resp = client.put(
            f"{NOTIFICATIONS}/preferences/reaction",
            headers=oh,
            json={"in_app_enabled": False, "email_enabled": False},
        )
        assert resp.status_code == 200
        resource = _create_resource(client, oh)

        _react(client, auth_headers(normal_user), "resource", resource["id"])
        assert _reaction_notifications(client, oh) == []

    def test_reaction_category_in_preferences(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.get(
            f"{NOTIFICATIONS}/preferences", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 200
        by_cat = {r["category"]: r for r in resp.json()}
        assert "reaction" in by_cat
        # Email defaults off for likes; in-app on.
        assert by_cat["reaction"]["in_app_enabled"] is True
        assert by_cat["reaction"]["email_enabled"] is False

    def test_email_outbox_written_when_reaction_email_enabled(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(settings, "NOTIFICATION_EMAILS_ENABLED", True)
        owner = make_user("owner")
        oh = auth_headers(owner)
        client.put(
            f"{NOTIFICATIONS}/preferences/reaction",
            headers=oh,
            json={"in_app_enabled": True, "email_enabled": True},
        )
        resource = _create_resource(client, oh)

        _react(client, auth_headers(normal_user), "resource", resource["id"])

        outbox = (
            db.query(notif_models.NotificationEmailOutbox)
            .filter(notif_models.NotificationEmailOutbox.recipient_user_id == owner.id)
            .all()
        )
        assert len(outbox) == 1
        assert outbox[0].category == NotificationCategory.REACTION.value


# --------------------------------------------------------------------------
# Moderation visibility
# --------------------------------------------------------------------------


@pytest.mark.moderation
class TestReactionVisibility:
    def test_cannot_react_to_unpublished_campaign(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("owner")
        request = _create_request(client, auth_headers(owner))

        # Draft (unpublished) campaign is invisible to a stranger: 404, and its
        # like-count is masked to zero.
        resp = client.post(
            REACTIONS,
            headers=auth_headers(normal_user),
            json={"entity_type": "request", "entity_id": request["id"]},
        )
        assert resp.status_code == 404

        state = _state(client, "request", [request["id"]], auth_headers(normal_user))[0]
        assert state["count"] == 0
        assert state["reacted"] is False
