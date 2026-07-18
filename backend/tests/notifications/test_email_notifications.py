"""Tests for notification email delivery, preferences, and unsubscribe.

Covers the multi-channel layer added on top of the in-app notifications:
per-category preferences gate whether an event produces an in-app row, an
email outbox row, or both; the drain worker sends queued emails; and signed
no-login unsubscribe links flip an email preference or unwatch an entity.
"""

import smtplib
import threading
import uuid
from collections.abc import Callable

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.config import settings
from app.notifications import models as notif_models, service, unsubscribe
from app.notifications.constants import (
    CATEGORY_DEFAULTS,
    NotificationCategory,
    NotificationReason,
    category_for,
)
from app.notifications.email import render_notification_email
from app.notifications.exceptions import InvalidUnsubscribeTokenExceptionError
from app.scheduled import runner, send_notification_emails
from app.users.constants import Locale
from app.users.models import User

RESOURCES = "/api/v1/resources"
COMMENTS = "/api/v1/comments"
NOTIFICATIONS = "/api/v1/notifications"
WATCHES = "/api/v1/watches"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _with_email(db: Session, user: User, email: str = "u@example.com") -> User:
    """Give a user an email address (make_user leaves it unset)."""
    user.email = email
    db.commit()
    db.refresh(user)
    return user


def _create_resource(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    resp = client.post(
        RESOURCES,
        headers=headers,
        json={"name": "Ferula", "source_url": "https://example.com/p.stl"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _comment(
    client: TestClient,
    headers: dict[str, str],
    entity_type: str,
    entity_id: object,
    body: str,
) -> None:
    resp = client.post(
        COMMENTS,
        headers=headers,
        json={"entity_type": entity_type, "entity_id": str(entity_id), "body": body},
    )
    assert resp.status_code == 201, resp.text


def _outbox(
    db: Session, recipient_id: uuid.UUID
) -> list[notif_models.NotificationEmailOutbox]:
    return (
        db.query(notif_models.NotificationEmailOutbox)
        .filter(notif_models.NotificationEmailOutbox.recipient_user_id == recipient_id)
        .all()
    )


def _inapp(db: Session, recipient_id: uuid.UUID) -> list[notif_models.Notification]:
    return (
        db.query(notif_models.Notification)
        .filter(notif_models.Notification.recipient_user_id == recipient_id)
        .all()
    )


def _set_pref(
    client: TestClient,
    headers: dict[str, str],
    category: str,
    *,
    in_app: bool,
    email: bool,
) -> None:
    resp = client.put(
        f"{NOTIFICATIONS}/preferences/{category}",
        headers=headers,
        json={"in_app_enabled": in_app, "email_enabled": email},
    )
    assert resp.status_code == 200, resp.text


# --------------------------------------------------------------------------
# Category mapping
# --------------------------------------------------------------------------


class TestCategoryMapping:
    def test_mention_reason_always_maps_to_mention(self):
        assert (
            category_for(NotificationReason.MENTION, "anything")
            is NotificationCategory.MENTION
        )

    @pytest.mark.parametrize(
        ("event", "expected"),
        [
            ("commented", NotificationCategory.COMMENT),
            ("status_changed", NotificationCategory.STATUS_CHANGE),
            ("item_added", NotificationCategory.ITEM_ADDED),
            ("tracking_update", NotificationCategory.TRACKING_UPDATE),
            ("request_submitted", NotificationCategory.REVIEW_QUEUE),
            ("request_reviewed", NotificationCategory.REQUEST_REVIEWED),
        ],
    )
    def test_event_maps_to_category(self, event: str, expected: NotificationCategory):
        assert category_for(NotificationReason.WATCH, event) is expected

    def test_unknown_event_falls_back_to_comment(self):
        assert (
            category_for(NotificationReason.WATCH, "brand_new_event")
            is NotificationCategory.COMMENT
        )


# --------------------------------------------------------------------------
# Channel gating
# --------------------------------------------------------------------------


class TestChannelGating:
    def test_mention_defaults_write_both_channels(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _comment(client, auth_headers(author), "resource", resource["id"], "@user1 hi")
        assert len(_inapp(db, normal_user.id)) == 1
        outbox = _outbox(db, normal_user.id)
        assert len(outbox) == 1
        assert outbox[0].category == NotificationCategory.MENTION.value

    def test_email_off_suppresses_outbox_only(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        headers = auth_headers(normal_user)
        _set_pref(client, headers, "mention", in_app=True, email=False)
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _comment(client, auth_headers(author), "resource", resource["id"], "@user1 hi")
        assert len(_inapp(db, normal_user.id)) == 1
        assert _outbox(db, normal_user.id) == []

    def test_in_app_off_still_emails(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        headers = auth_headers(normal_user)
        _set_pref(client, headers, "mention", in_app=False, email=True)
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _comment(client, auth_headers(author), "resource", resource["id"], "@user1 hi")
        assert _inapp(db, normal_user.id) == []
        assert len(_outbox(db, normal_user.id)) == 1

    def test_master_switch_off_suppresses_all_email(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(settings, "NOTIFICATION_EMAILS_ENABLED", False)
        _with_email(db, normal_user)
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _comment(client, auth_headers(author), "resource", resource["id"], "@user1 hi")
        assert len(_inapp(db, normal_user.id)) == 1
        assert _outbox(db, normal_user.id) == []

    def test_comment_on_watched_entity_emails_watcher(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        client.post(
            WATCHES,
            headers=auth_headers(normal_user),
            json={"entity_type": "resource", "entity_id": resource["id"]},
        )
        _comment(client, auth_headers(author), "resource", resource["id"], "hello all")
        outbox = _outbox(db, normal_user.id)
        assert len(outbox) == 1
        assert outbox[0].category == NotificationCategory.COMMENT.value


# --------------------------------------------------------------------------
# Preferences API
# --------------------------------------------------------------------------


class TestPreferencesApi:
    def test_list_defaults_for_regular_user_hides_review_queue(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.get(
            f"{NOTIFICATIONS}/preferences", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 200, resp.text
        rows = resp.json()
        categories = {r["category"] for r in rows}
        assert "review_queue" not in categories
        assert categories == {
            c.value
            for c in NotificationCategory
            if c is not NotificationCategory.REVIEW_QUEUE
        }
        by_cat = {r["category"]: r for r in rows}
        # Defaults come through: mention emails on, item_added emails off.
        assert by_cat["mention"]["email_enabled"] is True
        assert by_cat["item_added"]["email_enabled"] is False

    def test_admin_sees_review_queue(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.get(
            f"{NOTIFICATIONS}/preferences", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 200, resp.text
        categories = {r["category"] for r in resp.json()}
        assert "review_queue" in categories

    def test_update_persists(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        _set_pref(
            client, auth_headers(normal_user), "comment", in_app=False, email=False
        )
        resp = client.get(
            f"{NOTIFICATIONS}/preferences", headers=auth_headers(normal_user)
        )
        by_cat = {r["category"]: r for r in resp.json()}
        assert by_cat["comment"]["in_app_enabled"] is False
        assert by_cat["comment"]["email_enabled"] is False

    def test_update_is_idempotent_upsert(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        headers = auth_headers(normal_user)
        _set_pref(client, headers, "comment", in_app=True, email=False)
        _set_pref(client, headers, "comment", in_app=False, email=True)
        resp = client.get(
            f"{NOTIFICATIONS}/preferences", headers=auth_headers(normal_user)
        )
        by_cat = {r["category"]: r for r in resp.json()}
        assert by_cat["comment"]["in_app_enabled"] is False
        assert by_cat["comment"]["email_enabled"] is True

    def test_unknown_category_is_404(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.put(
            f"{NOTIFICATIONS}/preferences/not_a_category",
            headers=auth_headers(normal_user),
            json={"in_app_enabled": True, "email_enabled": True},
        )
        assert resp.status_code == 404, resp.text

    def test_preferences_require_auth(self, client: TestClient):
        assert client.get(f"{NOTIFICATIONS}/preferences").status_code == 401


# --------------------------------------------------------------------------
# Unsubscribe tokens + endpoints
# --------------------------------------------------------------------------


class TestUnsubscribe:
    def test_token_round_trip(self, normal_user: User):
        token = unsubscribe.make_unsubscribe_token(normal_user.id, "email:mention")
        user_id, action = unsubscribe.parse_unsubscribe_token(token)
        assert user_id == normal_user.id
        assert action == "email:mention"

    def test_apply_email_action_disables_email_keeps_in_app(
        self, db: Session, normal_user: User
    ):
        action = unsubscribe.email_action(NotificationCategory.MENTION)
        message = unsubscribe.apply_unsubscribe(db, normal_user.id, action)
        assert "correos" in message.lower()
        prefs = {
            c: (a, e) for c, a, e in service.list_preferences(db, user=normal_user)
        }
        in_app, email = prefs[NotificationCategory.MENTION]
        # In-app default was on and is preserved; only email is turned off.
        assert in_app is CATEGORY_DEFAULTS[NotificationCategory.MENTION][0]
        assert email is False

    def test_apply_email_action_preserves_existing_in_app_choice(
        self, db: Session, normal_user: User
    ):
        # User already turned in-app OFF for mentions; unsubscribing from the
        # email channel must not silently turn in-app back on.
        service.set_preference(
            db,
            user=normal_user,
            category=NotificationCategory.MENTION,
            in_app_enabled=False,
            email_enabled=True,
        )
        unsubscribe.apply_unsubscribe(
            db, normal_user.id, unsubscribe.email_action(NotificationCategory.MENTION)
        )
        prefs = {
            c: (a, e) for c, a, e in service.list_preferences(db, user=normal_user)
        }
        in_app, email = prefs[NotificationCategory.MENTION]
        assert in_app is False
        assert email is False

    def test_apply_unwatch_action(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        resource = _create_resource(client, auth_headers(normal_user))
        resource_id = uuid.UUID(str(resource["id"]))
        client.post(
            WATCHES,
            headers=auth_headers(normal_user),
            json={"entity_type": "resource", "entity_id": str(resource_id)},
        )
        action = unsubscribe.unwatch_action(EntityType.RESOURCE, resource_id)
        unsubscribe.apply_unsubscribe(db, normal_user.id, action)
        assert not service.is_watching(
            db,
            user=normal_user,
            entity_type=EntityType.RESOURCE,
            entity_id=resource_id,
        )

    def test_preview_and_post_endpoints(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
    ):
        token = unsubscribe.make_unsubscribe_token(normal_user.id, "email:comment")
        preview = client.get(
            f"{NOTIFICATIONS}/unsubscribe/preview", params={"token": token}
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["description"]
        applied = client.post(f"{NOTIFICATIONS}/unsubscribe", json={"token": token})
        assert applied.status_code == 200, applied.text
        assert applied.json()["message"]

    def test_tampered_token_is_400(self, client: TestClient):
        assert (
            client.post(
                f"{NOTIFICATIONS}/unsubscribe", json={"token": "not.a.jwt"}
            ).status_code
            == 400
        )
        assert (
            client.get(
                f"{NOTIFICATIONS}/unsubscribe/preview", params={"token": "nope"}
            ).status_code
            == 400
        )

    def test_wrong_purpose_token_rejected(self, normal_user: User):
        # A JWT signed with our key but for a different purpose must not work.
        bad = jwt.encode(
            {"sub": str(normal_user.id), "act": "email:mention", "purpose": "login"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(InvalidUnsubscribeTokenExceptionError):
            unsubscribe.parse_unsubscribe_token(bad)

    def test_apply_unknown_user_rejected(self, db: Session):
        with pytest.raises(InvalidUnsubscribeTokenExceptionError):
            unsubscribe.apply_unsubscribe(db, uuid.uuid4(), "email:mention")

    def test_apply_malformed_action_rejected(self, db: Session, normal_user: User):
        with pytest.raises(InvalidUnsubscribeTokenExceptionError):
            unsubscribe.apply_unsubscribe(db, normal_user.id, "email:bogus")

    def test_apply_malformed_unwatch_target_rejected(
        self, db: Session, normal_user: User
    ):
        with pytest.raises(InvalidUnsubscribeTokenExceptionError):
            unsubscribe.apply_unsubscribe(
                db, normal_user.id, "unwatch:resource:not-a-uuid"
            )

    def test_token_missing_claims_rejected(self, normal_user: User):
        no_sub = jwt.encode(
            {"act": "email:mention", "purpose": "unsubscribe"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        no_act = jwt.encode(
            {"sub": str(normal_user.id), "purpose": "unsubscribe"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        for bad in (no_sub, no_act):
            with pytest.raises(InvalidUnsubscribeTokenExceptionError):
                unsubscribe.parse_unsubscribe_token(bad)

    def test_describe_unwatch_action(self, db: Session, normal_user: User):
        action = unsubscribe.unwatch_action(EntityType.RESOURCE, uuid.uuid4())
        assert unsubscribe.describe_action(db, action)


class TestEmailRendering:
    def test_email_has_deep_link_and_manage_hyperlink(
        self, db: Session, make_user: MakeUser
    ):
        actor = make_user("mentioner")
        row = notif_models.NotificationEmailOutbox(
            recipient_user_id=uuid.uuid4(),
            actor_user_id=actor.id,
            entity_type="resource",
            entity_id=uuid.uuid4(),
            category=NotificationCategory.MENTION.value,
            event="mentioned",
            payload={
                "title": "Ferula",
                "link": "/parts/abc",
                "anchor": "comment-1",
            },
        )
        subject, text, html = render_notification_email(db, row)
        assert "mentioner" in subject
        # Deep link with the anchor in both parts.
        assert "/parts/abc#comment-1" in text
        assert "/parts/abc#comment-1" in html
        # HTML footer links to the preference center as a real hyperlink...
        assert 'href="http://localhost:3001/settings/notifications"' in html
        assert "Haz clic aquí" in html
        # ...and the old one-click unsubscribe links are gone.
        assert "/unsubscribe?token=" not in text
        assert "/unsubscribe?token=" not in html

    def test_comment_email_renders_the_comment_body(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _comment(
            client,
            auth_headers(author),
            "resource",
            resource["id"],
            "@user1 ¿aún vas a colaborar?",
        )
        row = _outbox(db, normal_user.id)[0]
        subject, text, html = render_notification_email(db, row)
        # Subject carries the actor AND the entity title (no mailbox threading).
        assert "author" in subject
        assert "Ferula" in subject
        # The comment body is shown in both parts, Jira-style.
        assert "¿aún vas a colaborar?" in text
        assert "¿aún vas a colaborar?" in html
        assert "@user1" in html  # mention preserved (and highlighted)
        # Button deep-links to the item.
        assert 'href="http://localhost:3001/parts' in html

    def test_long_comment_is_clipped(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        long_body = "@user1 " + ("muy largo " * 200)  # well over the display cap
        _comment(client, auth_headers(author), "resource", resource["id"], long_body)
        row = _outbox(db, normal_user.id)[0]
        _, text, _html = render_notification_email(db, row)
        assert "…" in text  # truncated with an ellipsis
        assert long_body not in text  # the full body is not shipped

    def test_tracking_update_email_includes_the_note(
        self, db: Session, make_user: MakeUser
    ):
        actor = make_user("maker")
        row = notif_models.NotificationEmailOutbox(
            recipient_user_id=uuid.uuid4(),
            actor_user_id=actor.id,
            entity_type="tracking_group",
            entity_id=uuid.uuid4(),
            category=NotificationCategory.TRACKING_UPDATE.value,
            event="tracking_update",
            payload={
                "title": "Ferula #3",
                "link": "/track/tok",
                "anchor": "record-1",
                "note": "listo, ya imprimí 5 unidades",
            },
        )
        subject, text, html = render_notification_email(db, row)
        assert "Ferula #3" in subject  # entity title in subject
        # The tracking note is shown in both parts, like a comment.
        assert "listo, ya imprimí 5 unidades" in text
        assert "listo, ya imprimí 5 unidades" in html

    def test_email_localized_to_english(self, db: Session, make_user: MakeUser):
        actor = make_user("maker")
        row = notif_models.NotificationEmailOutbox(
            recipient_user_id=uuid.uuid4(),
            actor_user_id=actor.id,
            entity_type="request",
            entity_id=uuid.uuid4(),
            category=NotificationCategory.MENTION.value,
            event="mentioned",
            payload={"title": "Splints VE", "link": "/requests/abc"},
        )
        subject, text, html = render_notification_email(db, row, Locale.EN)
        assert "mentioned you" in subject
        assert "Splints VE" in subject
        assert text.startswith("Hi,")
        assert "the request" in text  # English entity noun
        assert "click here" in html  # English footer link
        # Spanish copy must not leak into an English email.
        assert "Haz clic aquí" not in html

    def test_html_escapes_user_supplied_title(self, db: Session, make_user: MakeUser):
        actor = make_user("reviewer")
        row = notif_models.NotificationEmailOutbox(
            recipient_user_id=uuid.uuid4(),
            actor_user_id=actor.id,
            entity_type="request",
            entity_id=uuid.uuid4(),
            category=NotificationCategory.REQUEST_REVIEWED.value,
            event="request_reviewed",
            payload={"title": "<script>x</script>", "link": "/requests/abc"},
        )
        _, _, html = render_notification_email(db, row)
        assert "<script>x</script>" not in html
        assert "&lt;script&gt;" in html


# --------------------------------------------------------------------------
# Drain worker
# --------------------------------------------------------------------------


class TestDrainWorker:
    def _queue_mention(
        self,
        client: TestClient,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        target: str = "user1",
    ) -> None:
        author = make_user("author")
        resource = _create_resource(client, auth_headers(author))
        _comment(
            client, auth_headers(author), "resource", resource["id"], f"@{target} hi"
        )

    def test_sends_pending_and_stamps_sent_at(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        self._queue_mention(client, make_user, auth_headers)
        sent = service.send_pending_notification_emails(db)
        assert sent == 1
        row = _outbox(db, normal_user.id)[0]
        assert row.sent_at is not None
        assert row.last_error is None

    def test_recipient_without_email_is_retired(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        # normal_user has no email set here.
        self._queue_mention(client, make_user, auth_headers)
        sent = service.send_pending_notification_emails(db)
        assert sent == 0
        row = _outbox(db, normal_user.id)[0]
        assert row.sent_at is not None
        assert row.last_error is not None

    def test_smtp_failure_increments_attempts(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
        monkeypatch: pytest.MonkeyPatch,
    ):
        _with_email(db, normal_user)
        self._queue_mention(client, make_user, auth_headers)

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise smtplib.SMTPException("smtp down")

        monkeypatch.setattr("app.auth.email.send_email", _boom)
        sent = service.send_pending_notification_emails(db)
        assert sent == 0
        row = _outbox(db, normal_user.id)[0]
        assert row.attempts == 1
        assert row.sent_at is None
        assert row.last_error == "smtp down"

    def test_max_attempts_stops_retrying(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        _with_email(db, normal_user)
        self._queue_mention(client, make_user, auth_headers)
        row = _outbox(db, normal_user.id)[0]
        row.attempts = settings.NOTIFICATION_EMAIL_MAX_ATTEMPTS
        db.commit()
        sent = service.send_pending_notification_emails(db)
        assert sent == 0
        db.refresh(row)
        assert row.sent_at is None  # not picked up


# --------------------------------------------------------------------------
# Scheduled entrypoint + in-process worker
# --------------------------------------------------------------------------


class TestScheduledDrivers:
    def test_standalone_entrypoint_runs(self, db: Session):
        # Empty outbox in the freshly reset DB → nothing to send.
        assert send_notification_emails.run() == 0

    def test_worker_drains_then_stops(self, monkeypatch: pytest.MonkeyPatch):
        ran = threading.Event()

        def _fake(_db: Session, **_kwargs: object) -> int:
            ran.set()
            return 0

        monkeypatch.setattr(runner, "send_pending_notification_emails", _fake)
        worker = runner.EmailOutboxWorker(poll_seconds=60)
        worker.start()
        worker.start()  # idempotent: second start is a no-op
        assert ran.wait(timeout=5)
        worker.stop()

    def test_worker_survives_a_failed_pass(self, monkeypatch: pytest.MonkeyPatch):
        ran = threading.Event()

        def _boom(_db: Session, **_kwargs: object) -> int:
            ran.set()
            raise RuntimeError("drain blew up")

        monkeypatch.setattr(runner, "send_pending_notification_emails", _boom)
        worker = runner.EmailOutboxWorker(poll_seconds=60)
        worker.start()
        assert ran.wait(timeout=5)
        worker.stop()
        worker.stop()  # idempotent: second stop is safe
