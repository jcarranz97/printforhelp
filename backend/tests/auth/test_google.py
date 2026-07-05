"""Tests for the "Sign in with Google" flow."""

from collections.abc import Callable

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import google
from app.auth.exceptions import InvalidGoogleTokenExceptionError
from app.config import settings
from app.users.models import User

GOOGLE = "/api/v1/auth/google"
ME = "/api/v1/auth/me"


def _fake_claims(**overrides: object) -> dict[str, object]:
    claims: dict[str, object] = {
        "email": "newuser@example.com",
        "email_verified": True,
        "name": "New User",
        "sub": "google-sub-123",
        "iss": "https://accounts.google.com",
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def fake_google(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Make the backend accept a fixed id_token with the given claims."""

    def _install(**overrides: object) -> None:
        monkeypatch.setattr(
            "app.users.service.verify_google_id_token",
            lambda _token: _fake_claims(**overrides),
        )

    return _install


class TestGoogleLogin:
    def test_creates_account_on_first_login(
        self, client: TestClient, fake_google: Callable[..., None]
    ):
        fake_google()
        resp = client.post(GOOGLE, json={"id_token": "whatever"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        me = client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()
        assert me["email"] == "newuser@example.com"
        assert me["username"] == "newuser"
        assert me["full_name"] == "New User"
        assert me["role"] == "user"
        # Fresh Google account must still pick its own username.
        assert me["username_chosen"] is False

    def test_links_existing_email_account(
        self, client: TestClient, fake_google: Callable[..., None]
    ):
        # Register a password account first, then sign in with the same email.
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Maria",
                "username": "maria",
                "email": "maria@example.com",
                "password": "Password123",
            },
        )
        fake_google(email="maria@example.com", name="Maria G", sub="sub-maria")
        resp = client.post(GOOGLE, json={"id_token": "whatever"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        me = client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()
        # Same account (kept its original username), not a duplicate.
        assert me["username"] == "maria"

    def test_second_google_login_reuses_account(
        self, client: TestClient, fake_google: Callable[..., None]
    ):
        fake_google()
        first = client.post(GOOGLE, json={"id_token": "whatever"}).json()
        second = client.post(GOOGLE, json={"id_token": "whatever"}).json()
        first_me = client.get(
            ME, headers={"Authorization": f"Bearer {first['access_token']}"}
        ).json()
        second_me = client.get(
            ME, headers={"Authorization": f"Bearer {second['access_token']}"}
        ).json()
        assert first_me["id"] == second_me["id"]

    def test_username_collision_gets_a_suffix(
        self,
        client: TestClient,
        make_user: Callable[..., User],
        fake_google: Callable[..., None],
    ):
        make_user("newuser")  # occupies the natural username
        fake_google()  # email newuser@example.com -> base "newuser"
        resp = client.post(GOOGLE, json={"id_token": "whatever"})
        token = resp.json()["access_token"]
        me = client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()
        assert me["username"] == "newuser2"

    def test_short_email_local_part_gets_fallback_username(
        self, client: TestClient, fake_google: Callable[..., None]
    ):
        # "ab" is too short for a valid handle, so it falls back to "user";
        # "user" is reserved, so the collision loop lands on "user2".
        fake_google(email="ab@example.com")
        resp = client.post(GOOGLE, json={"id_token": "whatever"})
        token = resp.json()["access_token"]
        me = client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()
        assert me["username"] == "user2"

    def test_unverified_email_is_rejected(
        self, client: TestClient, fake_google: Callable[..., None]
    ):
        fake_google(email_verified=False)
        resp = client.post(GOOGLE, json={"id_token": "whatever"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_GOOGLE_TOKEN"

    def test_missing_email_is_rejected(
        self, client: TestClient, fake_google: Callable[..., None]
    ):
        fake_google(email=None)
        resp = client.post(GOOGLE, json={"id_token": "whatever"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_GOOGLE_TOKEN"

    def test_inactive_existing_user_is_rejected(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        fake_google: Callable[..., None],
    ):
        user = make_user("blocked", active=False)
        user.email = "blocked@example.com"
        db.commit()
        fake_google(email="blocked@example.com")
        resp = client.post(GOOGLE, json={"id_token": "whatever"})
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "INACTIVE_USER"


class TestVerifyGoogleIdToken:
    """Unit tests for the id_token verification itself."""

    def test_empty_client_id_rejects(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
        with pytest.raises(InvalidGoogleTokenExceptionError):
            google.verify_google_id_token("whatever")

    def _patch_signing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "my-client-id")

        class _Key:
            key = "signing-key"

        monkeypatch.setattr(
            google._jwks_client,
            "get_signing_key_from_jwt",
            lambda _t: _Key(),
        )

    def test_valid_token_returns_claims(self, monkeypatch: pytest.MonkeyPatch):
        self._patch_signing_key(monkeypatch)
        monkeypatch.setattr(
            google.jwt,
            "decode",
            lambda *a, **k: {"iss": "accounts.google.com", "email": "x@y.com"},
        )
        claims = google.verify_google_id_token("token")
        assert claims["email"] == "x@y.com"

    def test_wrong_issuer_rejects(self, monkeypatch: pytest.MonkeyPatch):
        self._patch_signing_key(monkeypatch)
        monkeypatch.setattr(
            google.jwt, "decode", lambda *a, **k: {"iss": "evil.example.com"}
        )
        with pytest.raises(InvalidGoogleTokenExceptionError):
            google.verify_google_id_token("token")

    def test_bad_signature_rejects(self, monkeypatch: pytest.MonkeyPatch):
        self._patch_signing_key(monkeypatch)

        def _raise(*_a: object, **_k: object) -> None:
            raise jwt.InvalidSignatureError("nope")

        monkeypatch.setattr(google.jwt, "decode", _raise)
        with pytest.raises(InvalidGoogleTokenExceptionError):
            google.verify_google_id_token("token")
