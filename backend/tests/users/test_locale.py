"""Tests for the self-service preferred-locale endpoint (UI + email language)."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User

USERS = "/api/v1/users"
ME = "/api/v1/auth/me"

AuthHeaders = Callable[[User], dict[str, str]]


class TestSelfLocale:
    def test_set_locale_updates_account(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        # Seeded users default to Spanish.
        assert client.get(ME, headers=h).json()["preferred_locale"] == "es"

        resp = client.put(f"{USERS}/me/locale", headers=h, json={"locale": "en"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["preferred_locale"] == "en"
        # It sticks and shows up on /auth/me.
        assert client.get(ME, headers=h).json()["preferred_locale"] == "en"

    def test_set_locale_requires_auth(self, client: TestClient):
        assert (
            client.put(f"{USERS}/me/locale", json={"locale": "en"}).status_code == 401
        )

    def test_invalid_locale_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.put(
            f"{USERS}/me/locale",
            headers=auth_headers(normal_user),
            json={"locale": "fr"},
        )
        assert resp.status_code == 422, resp.text
