"""Tests for watch subscriptions, @mentions, and in-app notifications."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.activity.models import Comment
from app.notifications import models as notif_models, service
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
RESOURCES = "/api/v1/resources"
COMMENTS = "/api/v1/comments"
NOTIFICATIONS = "/api/v1/notifications"
WATCHES = "/api/v1/watches"
USERS = "/api/v1/users"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _create_center(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
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


def _post_comment(
    client: TestClient,
    headers: dict[str, str],
    entity_type: str,
    entity_id: object,
    body: str = "Hello",
) -> dict[str, object]:
    resp = client.post(
        COMMENTS,
        headers=headers,
        json={"entity_type": entity_type, "entity_id": str(entity_id), "body": body},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _watch(
    client: TestClient, headers: dict[str, str], entity_type: str, entity_id: object
) -> None:
    resp = client.post(
        WATCHES,
        headers=headers,
        json={"entity_type": entity_type, "entity_id": str(entity_id)},
    )
    assert resp.status_code == 204, resp.text


def _notifications(
    client: TestClient, headers: dict[str, str], **params: object
) -> list:
    resp = client.get(NOTIFICATIONS, headers=headers, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestWatchEndpoints:
    def test_watch_unwatch_and_status(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        rid = resource["id"]
        headers = auth_headers(normal_user)

        _watch(client, headers, "resource", rid)
        status = client.get(f"{WATCHES}/resource/{rid}", headers=headers)
        assert status.status_code == 200
        assert status.json()["watching"] is True

        # Idempotent second watch.
        _watch(client, headers, "resource", rid)

        unwatch = client.delete(f"{WATCHES}/resource/{rid}", headers=headers)
        assert unwatch.status_code == 204
        status = client.get(f"{WATCHES}/resource/{rid}", headers=headers)
        assert status.json()["watching"] is False

        # Unwatch again is a harmless no-op.
        again = client.delete(f"{WATCHES}/resource/{rid}", headers=headers)
        assert again.status_code == 204

    def test_watch_reactivates_after_unwatch(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        rid = resource["id"]
        headers = auth_headers(normal_user)
        _watch(client, headers, "resource", rid)
        client.delete(f"{WATCHES}/resource/{rid}", headers=headers)
        _watch(client, headers, "resource", rid)
        status = client.get(f"{WATCHES}/resource/{rid}", headers=headers)
        assert status.json()["watching"] is True

    def test_watch_missing_entity_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            WATCHES,
            headers=auth_headers(normal_user),
            json={"entity_type": "resource", "entity_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "INVALID_WATCH_TARGET"

    def test_watch_requires_auth(self, client: TestClient):
        resp = client.post(
            WATCHES,
            json={"entity_type": "resource", "entity_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401


class TestCommentNotifications:
    def test_watcher_notified_on_comment(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        # normal_user (user1) watches the resource.
        _watch(client, auth_headers(normal_user), "resource", resource["id"])

        _post_comment(client, auth_headers(author), "resource", resource["id"])

        watcher_notes = _notifications(client, auth_headers(normal_user))
        assert len(watcher_notes) == 1
        note = watcher_notes[0]
        assert note["reason"] == "watch"
        assert note["event"] == "commented"
        assert note["actor"]["username"] == "author"
        assert note["title"] == "Ferula"
        assert note["link"] == f"/parts/{resource['id']}"
        assert note["read_at"] is None

        # The actor is never notified about their own comment.
        author_notes = _notifications(client, auth_headers(author))
        assert author_notes == []

    def test_commenting_auto_subscribes(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        # normal_user comments -> auto-watches the resource.
        _post_comment(client, auth_headers(normal_user), "resource", resource["id"])
        # author comments -> the auto-subscribed normal_user is notified.
        _post_comment(client, auth_headers(author), "resource", resource["id"])

        notes = _notifications(client, auth_headers(normal_user))
        assert len(notes) == 1
        assert notes[0]["event"] == "commented"

    def test_mention_notifies_named_user(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _post_comment(
            client,
            auth_headers(author),
            "resource",
            resource["id"],
            body="hey @user1 please help",
        )
        notes = _notifications(client, auth_headers(normal_user))
        assert len(notes) == 1
        assert notes[0]["reason"] == "mention"
        assert notes[0]["event"] == "mentioned"

    def test_mention_dedupes_against_watch(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _watch(client, auth_headers(normal_user), "resource", resource["id"])
        _post_comment(
            client,
            auth_headers(author),
            "resource",
            resource["id"],
            body="ping @user1",
        )
        notes = _notifications(client, auth_headers(normal_user))
        # Exactly one notification: the mention, not also a watch ping.
        assert len(notes) == 1
        assert notes[0]["reason"] == "mention"

    def test_repeated_mention_notifies_once(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _post_comment(
            client,
            auth_headers(author),
            "resource",
            resource["id"],
            body="@user1 hey @user1 again",
        )
        notes = _notifications(client, auth_headers(normal_user))
        assert len(notes) == 1

    def test_self_mention_and_unknown_mention_ignored(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        _post_comment(
            client,
            auth_headers(normal_user),
            "resource",
            resource["id"],
            body="note to self @user1 and @nobodyhere",
        )
        notes = _notifications(client, auth_headers(normal_user))
        assert notes == []

    def test_edit_notifies_only_new_mentions(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        bob = make_user("bob")
        resource = _create_resource(client, auth_headers(author))
        comment = _post_comment(
            client,
            auth_headers(author),
            "resource",
            resource["id"],
            body="hi @user1",
        )
        # user1 already notified once.
        assert len(_notifications(client, auth_headers(normal_user))) == 1

        resp = client.patch(
            f"{COMMENTS}/{comment['id']}",
            headers=auth_headers(author),
            json={"body": "hi @user1 and @bob"},
        )
        assert resp.status_code == 200
        # user1 was already mentioned -> no second notification.
        assert len(_notifications(client, auth_headers(normal_user))) == 1
        # bob is a newly added mention -> notified.
        assert len(_notifications(client, auth_headers(bob))) == 1


class TestStatusChangeNotifications:
    def test_watcher_notified_on_shipment_status_change(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = normal_user
        center = _create_center(client, auth_headers(owner))
        shipment = _create_shipment(client, center["id"], auth_headers(owner))
        watcher = make_user("watcher")
        _watch(client, auth_headers(watcher), "shipment", shipment["id"])

        resp = client.patch(
            f"{CENTERS}/{center['id']}/shipments/{shipment['id']}",
            headers=auth_headers(owner),
            json={"status": "closed"},
        )
        assert resp.status_code == 200

        notes = _notifications(client, auth_headers(watcher))
        assert len(notes) == 1
        assert notes[0]["event"] == "status_changed"
        assert notes[0]["entity_type"] == "shipment"
        assert notes[0]["link"].endswith(f"/shipments/{shipment['id']}")


class TestNotificationReads:
    def test_unread_count_and_mark_read(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _watch(client, auth_headers(normal_user), "resource", resource["id"])
        _post_comment(
            client, auth_headers(author), "resource", resource["id"], body="a"
        )
        _post_comment(
            client, auth_headers(author), "resource", resource["id"], body="b"
        )

        headers = auth_headers(normal_user)
        count = client.get(f"{NOTIFICATIONS}/unread-count", headers=headers)
        assert count.json()["count"] == 2

        unread = _notifications(client, headers, unread_only=True)
        assert len(unread) == 2

        first_id = unread[0]["id"]
        resp = client.post(
            f"{NOTIFICATIONS}/read", headers=headers, json={"ids": [first_id]}
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 1
        assert (
            client.get(f"{NOTIFICATIONS}/unread-count", headers=headers).json()["count"]
            == 1
        )

        resp = client.post(f"{NOTIFICATIONS}/read", headers=headers, json={"all": True})
        assert resp.json()["updated"] == 1
        assert (
            client.get(f"{NOTIFICATIONS}/unread-count", headers=headers).json()["count"]
            == 0
        )

    def test_mark_read_requires_ids_or_all(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            f"{NOTIFICATIONS}/read", headers=auth_headers(normal_user), json={}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_MARK_READ_REQUEST"

    def test_list_requires_auth(self, client: TestClient):
        assert client.get(NOTIFICATIONS).status_code == 401
        assert client.get(f"{NOTIFICATIONS}/unread-count").status_code == 401


class TestUserSearch:
    def test_search_matches_prefix_and_excludes_anonymous(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        make_user("maria")
        make_user("mario")
        make_user("anonymous")
        resp = client.get(
            f"{USERS}/search", headers=auth_headers(normal_user), params={"q": "mar"}
        )
        assert resp.status_code == 200
        names = {u["username"] for u in resp.json()}
        assert names == {"maria", "mario"}

    def test_empty_query_returns_users(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.get(
            f"{USERS}/search",
            headers=auth_headers(normal_user),
            params={"limit": 5},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_search_requires_auth(self, client: TestClient):
        assert client.get(f"{USERS}/search").status_code == 401


class TestServiceBranches:
    """Unit-level coverage for branches awkward to reach over HTTP."""

    def test_resolve_link_fallbacks_for_missing_entities(self, db: Session):
        missing = uuid.uuid4()
        for entity_type, prefix in [
            (EntityType.COLLECTION_CENTER, "/centers/"),
            (EntityType.RESOURCE, "/parts/"),
            (EntityType.REQUEST, "/requests/"),
        ]:
            title, link = service._resolve_link_and_title(db, entity_type, missing)
            assert link == f"{prefix}{missing}"
            assert title  # non-empty fallback label
        # A missing shipment cannot resolve its parent center.
        title, link = service._resolve_link_and_title(db, EntityType.SHIPMENT, missing)
        assert (title, link) == ("Shipment", "/centers")

    def test_fan_out_skips_inactive_recipients(self, db: Session, make_user: MakeUser):
        ghost = make_user("ghost", active=False)
        entity_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        service.ensure_watch(db, ghost.id, EntityType.RESOURCE, entity_id)
        service.fan_out_to_watchers(
            db,
            entity_type=EntityType.RESOURCE,
            entity_id=entity_id,
            actor_user_id=actor_id,
            event="commented",
        )
        db.flush()
        assert (
            service.unread_count(db, user=ghost) == 0
        )  # inactive watcher gets nothing

    def test_fan_out_no_watchers_is_noop(self, db: Session):
        service.fan_out_to_watchers(
            db,
            entity_type=EntityType.RESOURCE,
            entity_id=uuid.uuid4(),
            actor_user_id=uuid.uuid4(),
            event="commented",
        )
        # No exception, nothing to assert beyond a clean return.

    def test_extract_mentions_caps_and_dedupes(self):
        body = " ".join(f"@user{i}" for i in range(30)) + " @user0"
        names = service._extract_mentions(body)
        assert names[0] == "user0"
        assert len(names) == 20  # MAX_MENTIONS_PER_COMMENT
        assert len(names) == len(set(names))

    def test_mention_to_inactive_user_skipped(self, db: Session, make_user: MakeUser):
        author = make_user("writer")
        make_user("sleeper", active=False)
        comment = Comment(
            entity_type=EntityType.RESOURCE.value,
            entity_id=uuid.uuid4(),
            author_user_id=author.id,
            body="ping @sleeper",
        )
        db.add(comment)
        db.flush()
        notified = service.create_mention_notifications(
            db, comment=comment, actor=author
        )
        assert notified == set()

    def test_before_filter_paginates(self, db: Session, make_user: MakeUser):
        recipient = make_user("recip")
        actor = make_user("actor")
        older = notif_models.Notification(
            recipient_user_id=recipient.id,
            actor_user_id=actor.id,
            entity_type=EntityType.RESOURCE.value,
            entity_id=uuid.uuid4(),
            reason="watch",
            event="commented",
            payload={"title": "t", "link": "/parts/x"},
            created_at=datetime.now(UTC) - timedelta(hours=1),
        )
        newer = notif_models.Notification(
            recipient_user_id=recipient.id,
            actor_user_id=actor.id,
            entity_type=EntityType.RESOURCE.value,
            entity_id=uuid.uuid4(),
            reason="watch",
            event="commented",
            payload={"title": "t", "link": "/parts/y"},
            created_at=datetime.now(UTC),
        )
        db.add_all([older, newer])
        db.commit()

        page = service.list_for_user(db, user=recipient, before=newer.created_at)
        assert [n.id for n in page] == [older.id]
