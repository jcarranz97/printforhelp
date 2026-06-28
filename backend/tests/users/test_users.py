"""Tests for the admin user-management endpoints."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User
from tests.conftest import DEFAULT_TEST_PASSWORD

USERS = "/api/v1/users"


class TestListUsers:
    def test_requires_auth(self, client: TestClient):
        assert client.get(USERS).status_code == 401

    def test_non_admin_forbidden(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.get(USERS, headers=auth_headers(normal_user))
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ROLE_REQUIRED"

    def test_admin_can_list(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.get(USERS, headers=auth_headers(admin_user))
        assert resp.status_code == 200
        usernames = {u["username"] for u in resp.json()}
        assert {"admin", "user1"} <= usernames


class TestCreateUser:
    def test_create_success(
        self,
        client: TestClient,
        admin_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.post(
            USERS,
            headers=auth_headers(admin_user),
            json={
                "username": "bob",
                "password": "BobPass123",
                "role": "maintainer",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "bob"
        assert body["role"] == "maintainer"
        assert body["active"] is True

    def test_duplicate_username(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.post(
            USERS,
            headers=auth_headers(admin_user),
            json={"username": "user1", "password": "Another123"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_TAKEN"

    def test_weak_password(
        self,
        client: TestClient,
        admin_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.post(
            USERS,
            headers=auth_headers(admin_user),
            json={"username": "weakuser", "password": "nodigitshere"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "WEAK_PASSWORD"

    def test_non_admin_forbidden(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.post(
            USERS,
            headers=auth_headers(normal_user),
            json={"username": "bob", "password": "BobPass123"},
        )
        assert resp.status_code == 403


class TestGetUser:
    def test_not_found(
        self,
        client: TestClient,
        admin_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.get(f"{USERS}/{uuid.uuid4()}", headers=auth_headers(admin_user))
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "USER_NOT_FOUND"


class TestUpdateRole:
    def test_promote_user(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            f"{USERS}/{normal_user.id}/role",
            headers=auth_headers(admin_user),
            json={"role": "maintainer"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "maintainer"

    def test_demote_last_admin_blocked(
        self,
        client: TestClient,
        admin_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            f"{USERS}/{admin_user.id}/role",
            headers=auth_headers(admin_user),
            json={"role": "user"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "LOCKOUT_PROTECTION"

    def test_demote_admin_when_another_exists(
        self,
        client: TestClient,
        admin_user: User,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        other_admin = make_user("admin2", role=admin_user.role)
        resp = client.put(
            f"{USERS}/{other_admin.id}/role",
            headers=auth_headers(admin_user),
            json={"role": "user"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "user"


class TestResetPassword:
    def test_admin_resets_password(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            f"{USERS}/{normal_user.id}/password",
            headers=auth_headers(admin_user),
            json={"new_password": "ResetByAdmin1"},
        )
        assert resp.status_code == 200
        # The user can log in with the admin-set password.
        login = client.post(
            "/api/v1/auth/login",
            data={"username": "user1", "password": "ResetByAdmin1"},
        )
        assert login.status_code == 200

    def test_weak_password_rejected(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            f"{USERS}/{normal_user.id}/password",
            headers=auth_headers(admin_user),
            json={"new_password": "alllettersnodigit"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "WEAK_PASSWORD"

    def test_non_admin_forbidden(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.put(
            f"{USERS}/{normal_user.id}/password",
            headers=auth_headers(normal_user),
            json={"new_password": "Whatever123"},
        )
        assert resp.status_code == 403


class TestDeactivateReactivate:
    def test_deactivate_user(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.post(
            f"{USERS}/{normal_user.id}/deactivate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False
        # Deactivated user cannot log in (FR-013).
        login = client.post(
            "/api/v1/auth/login",
            data={"username": "user1", "password": DEFAULT_TEST_PASSWORD},
        )
        assert login.status_code == 403

    def test_deactivate_last_admin_blocked(
        self,
        client: TestClient,
        admin_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        resp = client.post(
            f"{USERS}/{admin_user.id}/deactivate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "LOCKOUT_PROTECTION"

    def test_reactivate_user(
        self,
        client: TestClient,
        admin_user: User,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        target = make_user("dormant", active=False)
        resp = client.post(
            f"{USERS}/{target.id}/reactivate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is True
