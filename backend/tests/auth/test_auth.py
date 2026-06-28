"""Tests for the auth endpoints."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User
from tests.conftest import DEFAULT_TEST_PASSWORD

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
PASSWORD = "/api/v1/auth/me/password"
REGISTER = "/api/v1/auth/register"


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

    def test_login_with_email(self, client: TestClient):
        client.post(
            REGISTER,
            json={
                "full_name": "Maria",
                "username": "maria",
                "email": "Maria@Example.com",
                "password": "Password123",
            },
        )
        # Email is matched case-insensitively.
        resp = client.post(
            LOGIN, data={"username": "maria@example.com", "password": "Password123"}
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    def test_login_registered_user_by_username(self, client: TestClient):
        client.post(
            REGISTER,
            json={
                "full_name": "Maria",
                "username": "maria",
                "email": "maria@example.com",
                "password": "Password123",
            },
        )
        # The chosen username also works as a login identifier.
        resp = client.post(LOGIN, data={"username": "maria", "password": "Password123"})
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    def test_login_username_case_insensitive(self, client: TestClient):
        client.post(
            REGISTER,
            json={
                "full_name": "Maria",
                "username": "Maria",
                "email": "maria@example.com",
                "password": "Password123",
            },
        )
        # Username stored as "Maria" but login is case-insensitive.
        resp = client.post(LOGIN, data={"username": "MARIA", "password": "Password123"})
        assert resp.status_code == 200
        assert resp.json()["access_token"]


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


class TestRegister:
    def test_register_success(self, client: TestClient):
        resp = client.post(
            REGISTER,
            json={
                "full_name": "Maria Pérez",
                "username": "mariap",
                "email": "maria@example.com",
                "password": "Password123",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        # The returned token authenticates the brand-new account.
        me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200
        profile = me.json()
        assert profile["username"] == "mariap"
        assert profile["email"] == "maria@example.com"
        assert profile["full_name"] == "Maria Pérez"
        assert profile["role"] == "user"

    def test_register_normalizes_fields(self, client: TestClient):
        resp = client.post(
            REGISTER,
            json={
                "full_name": "  Ana  ",
                "username": "  ana  ",
                "email": "  ANA@Example.com ",
                "password": "Password123",
            },
        )
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        profile = client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()
        assert profile["username"] == "ana"
        assert profile["email"] == "ana@example.com"
        assert profile["full_name"] == "Ana"

    def test_register_duplicate_email(self, client: TestClient):
        payload = {
            "full_name": "Ana",
            "username": "ana",
            "email": "ana@example.com",
            "password": "Password123",
        }
        assert client.post(REGISTER, json=payload).status_code == 201
        # Same email (different case), different username -> EMAIL_TAKEN.
        resp = client.post(
            REGISTER,
            json={**payload, "username": "ana2", "email": "ANA@example.com"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "EMAIL_TAKEN"

    def test_register_duplicate_username(self, client: TestClient):
        payload = {
            "full_name": "Ana",
            "username": "ana",
            "email": "ana@example.com",
            "password": "Password123",
        }
        assert client.post(REGISTER, json=payload).status_code == 201
        # Same username, different email -> USERNAME_TAKEN.
        resp = client.post(
            REGISTER,
            json={**payload, "email": "ana.other@example.com"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_TAKEN"

    def test_register_duplicate_username_case_insensitive(self, client: TestClient):
        payload = {
            "full_name": "Maria",
            "username": "Maria",
            "email": "maria@example.com",
            "password": "Password123",
        }
        assert client.post(REGISTER, json=payload).status_code == 201
        # Different case + different email still collides on the username.
        resp = client.post(
            REGISTER,
            json={**payload, "username": "MARIA", "email": "maria2@example.com"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_TAKEN"

    def test_register_username_taken_by_admin_account(
        self, client: TestClient, make_user: Callable[..., User]
    ):
        # An admin-provisioned account already claimed this username.
        make_user("existing")
        resp = client.post(
            REGISTER,
            json={
                "full_name": "Clash",
                "username": "existing",
                "email": "clash@example.com",
                "password": "Password123",
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_TAKEN"

    def test_register_weak_password(self, client: TestClient):
        resp = client.post(
            REGISTER,
            json={
                "full_name": "Ana",
                "username": "ana",
                "email": "ana@example.com",
                "password": "allletters",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "WEAK_PASSWORD"

    def test_register_invalid_email(self, client: TestClient):
        resp = client.post(
            REGISTER,
            json={
                "full_name": "Ana",
                "username": "ana",
                "email": "not-an-email",
                "password": "Password123",
            },
        )
        assert resp.status_code == 422
