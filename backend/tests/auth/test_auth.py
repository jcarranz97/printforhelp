"""Tests for the auth endpoints."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User
from tests.conftest import DEFAULT_TEST_PASSWORD

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
PASSWORD = "/api/v1/auth/me/password"


class TestLogin:
    def test_login_success(self, client: TestClient, normal_user: User):
        resp = client.post(
            LOGIN,
            data={
                "username": "user1",
                "password": DEFAULT_TEST_PASSWORD,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["expires_in"] > 0

    def test_login_wrong_password(self, client: TestClient, normal_user: User):
        resp = client.post(LOGIN, data={"username": "user1", "password": "wrongpass1"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_login_unknown_user(self, client: TestClient):
        resp = client.post(LOGIN, data={"username": "ghost", "password": "whatever1"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_login_inactive_user(
        self, client: TestClient, make_user: Callable[..., User]
    ):
        make_user("inactive1", active=False)
        resp = client.post(
            LOGIN,
            data={"username": "inactive1", "password": DEFAULT_TEST_PASSWORD},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "INACTIVE_USER"


class TestMe:
    def test_requires_auth(self, client: TestClient):
        resp = client.get(ME)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_TOKEN"

    def test_me_success(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.get(ME, headers=auth_headers(normal_user))
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "user1"
        assert body["role"] == "user"
        assert "password_hash" not in body


class TestChangePassword:
    def test_change_password_success(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            PASSWORD,
            headers=auth_headers(normal_user),
            json={
                "current_password": DEFAULT_TEST_PASSWORD,
                "new_password": "BrandNew123",
            },
        )
        assert resp.status_code == 200
        # Old password no longer works; new one does.
        old = client.post(
            LOGIN, data={"username": "user1", "password": DEFAULT_TEST_PASSWORD}
        )
        assert old.status_code == 401
        new = client.post(LOGIN, data={"username": "user1", "password": "BrandNew123"})
        assert new.status_code == 200

    def test_wrong_current_password(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            PASSWORD,
            headers=auth_headers(normal_user),
            json={
                "current_password": "nope12345",
                "new_password": "BrandNew123",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INCORRECT_PASSWORD"

    def test_weak_new_password(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            PASSWORD,
            headers=auth_headers(normal_user),
            json={
                "current_password": DEFAULT_TEST_PASSWORD,
                "new_password": "alllettersnodigit",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "WEAK_PASSWORD"


class TestRegisterDisabled:
    def test_register_disabled(self, client: TestClient):
        resp = client.post("/api/v1/auth/register")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "REGISTRATION_DISABLED"
