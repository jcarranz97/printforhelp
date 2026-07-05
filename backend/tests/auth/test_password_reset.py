"""Tests for the forgot-password / reset-password flow."""

import smtplib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import PasswordResetToken
from app.users.models import User

FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"

NEW_PASSWORD = "BrandNew123"


@pytest.fixture
def capture_reset_url(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Capture the reset URL instead of emailing it."""
    captured: dict[str, str] = {}

    def _fake(to: str, reset_url: str) -> None:
        captured["to"] = to
        captured["url"] = reset_url

    monkeypatch.setattr("app.auth.service.send_password_reset_email", _fake)
    return captured


def _register(client: TestClient, email: str = "maria@example.com") -> None:
    client.post(
        REGISTER,
        json={
            "full_name": "Maria",
            "username": "maria",
            "email": email,
            "password": "Password123",
        },
    )


def _token_from(url: str) -> str:
    return url.split("token=")[1]


class TestForgotPassword:
    def test_sends_link_for_known_email(
        self, client: TestClient, capture_reset_url: dict[str, str]
    ):
        _register(client)
        resp = client.post(FORGOT, json={"email": "maria@example.com"})
        assert resp.status_code == 200
        assert capture_reset_url["to"] == "maria@example.com"
        assert "/reset-password?token=" in capture_reset_url["url"]

    def test_email_is_matched_case_insensitively(
        self, client: TestClient, capture_reset_url: dict[str, str]
    ):
        _register(client, email="maria@example.com")
        resp = client.post(FORGOT, json={"email": "MARIA@Example.com"})
        assert resp.status_code == 200
        assert capture_reset_url.get("to") == "maria@example.com"

    def test_unknown_email_still_returns_ok_and_sends_nothing(
        self, client: TestClient, capture_reset_url: dict[str, str]
    ):
        resp = client.post(FORGOT, json={"email": "nobody@example.com"})
        assert resp.status_code == 200
        assert capture_reset_url == {}

    def test_inactive_account_gets_no_link(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        capture_reset_url: dict[str, str],
    ):
        user = make_user("ghost", active=False)
        user.email = "ghost@example.com"
        db.commit()
        resp = client.post(FORGOT, json={"email": "ghost@example.com"})
        assert resp.status_code == 200
        assert capture_reset_url == {}

    def test_send_failure_still_returns_ok(
        self, client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
    ):
        # A dead mail server must not break the endpoint or leak which
        # emails exist — it still returns the same generic 200.
        _register(client)

        def _boom(_to: str, _url: str) -> None:
            raise smtplib.SMTPAuthenticationError(535, b"auth failed")

        monkeypatch.setattr("app.auth.service.send_password_reset_email", _boom)
        resp = client.post(FORGOT, json={"email": "maria@example.com"})
        assert resp.status_code == 200
        # The token was still created despite the send failing.
        assert db.query(PasswordResetToken).count() == 1

    def test_requesting_again_retires_the_previous_token(
        self, client: TestClient, db: Session, capture_reset_url: dict[str, str]
    ):
        _register(client)
        client.post(FORGOT, json={"email": "maria@example.com"})
        first_token = _token_from(capture_reset_url["url"])
        client.post(FORGOT, json={"email": "maria@example.com"})
        # The first link no longer works once a newer one is issued.
        resp = client.post(
            RESET, json={"token": first_token, "new_password": NEW_PASSWORD}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"


class TestResetPassword:
    def test_reset_success(self, client: TestClient, capture_reset_url: dict[str, str]):
        _register(client)
        client.post(FORGOT, json={"email": "maria@example.com"})
        token = _token_from(capture_reset_url["url"])

        resp = client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
        assert resp.status_code == 200

        # New password works, old one does not.
        assert (
            client.post(
                LOGIN, data={"username": "maria", "password": "Password123"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                LOGIN, data={"username": "maria", "password": NEW_PASSWORD}
            ).status_code
            == 200
        )

    def test_token_cannot_be_reused(
        self, client: TestClient, capture_reset_url: dict[str, str]
    ):
        _register(client)
        client.post(FORGOT, json={"email": "maria@example.com"})
        token = _token_from(capture_reset_url["url"])
        assert (
            client.post(
                RESET, json={"token": token, "new_password": NEW_PASSWORD}
            ).status_code
            == 200
        )
        resp = client.post(RESET, json={"token": token, "new_password": "Another123"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"

    def test_unknown_token_is_rejected(self, client: TestClient):
        resp = client.post(
            RESET, json={"token": "not-a-real-token", "new_password": NEW_PASSWORD}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"

    def test_expired_token_is_rejected(
        self, client: TestClient, db: Session, make_user: Callable[..., User]
    ):
        user = make_user("pedro")
        raw = "expired-token-value"
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=service._hash_reset_token(raw),
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        db.commit()
        resp = client.post(RESET, json={"token": raw, "new_password": NEW_PASSWORD})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"

    def test_token_for_deactivated_user_is_rejected(
        self, client: TestClient, db: Session, make_user: Callable[..., User]
    ):
        user = make_user("juan")
        raw = "valid-token-value"
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=service._hash_reset_token(raw),
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        user.active = False
        db.commit()
        resp = client.post(RESET, json={"token": raw, "new_password": NEW_PASSWORD})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"

    def test_weak_new_password_is_rejected(
        self, client: TestClient, capture_reset_url: dict[str, str]
    ):
        _register(client)
        client.post(FORGOT, json={"email": "maria@example.com"})
        token = _token_from(capture_reset_url["url"])
        resp = client.post(
            RESET, json={"token": token, "new_password": "alllettersnodigit"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "WEAK_PASSWORD"
