"""Tests for the generic per-user flags (traits + capabilities)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.permissions import has_capability
from app.users.flags import FlagKey
from app.users.models import User
from app.users.service import get_flag

USERS = "/api/v1/users"
ME = "/api/v1/auth/me"

AuthHeaders = Callable[[User], dict[str, str]]


class TestSelfFlags:
    def test_me_flags_empty_by_default(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        body = client.get(ME, headers=auth_headers(normal_user)).json()
        # Unknown = absent; the maker prompt has not been answered.
        assert body["flags"] == {}

    def test_set_maker_yes_then_no(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resp = client.put(f"{USERS}/me/flags/maker", headers=h, json={"value": True})
        assert resp.status_code == 200, resp.text
        assert resp.json()["flags"]["maker"] is True
        assert client.get(ME, headers=h).json()["flags"]["maker"] is True

        # Answering "no" updates the same row (still an answer, not unknown).
        resp = client.put(f"{USERS}/me/flags/maker", headers=h, json={"value": False})
        assert resp.json()["flags"]["maker"] is False
        assert client.get(ME, headers=h).json()["flags"]["maker"] is False

    def test_requires_auth(self, client: TestClient):
        resp = client.put(f"{USERS}/me/flags/maker", json={"value": True})
        assert resp.status_code == 401

    def test_cannot_self_set_capability(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.put(
            f"{USERS}/me/flags/can_add_part",
            headers=auth_headers(normal_user),
            json={"value": True},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FLAG_NOT_SELF_ASSIGNABLE"

    def test_unknown_flag_rejected(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.put(
            f"{USERS}/me/flags/not_a_real_flag",
            headers=auth_headers(normal_user),
            json={"value": True},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNKNOWN_FLAG"


class TestAdminFlags:
    def test_admin_can_grant_capability(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        resp = client.put(
            f"{USERS}/{normal_user.id}/flags/can_add_part",
            headers=auth_headers(admin_user),
            json={"value": True},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["flags"]["can_add_part"] is True
        # The grant shows up on the target user's own /auth/me.
        mine = client.get(ME, headers=auth_headers(normal_user)).json()
        assert mine["flags"]["can_add_part"] is True

    def test_non_admin_cannot_use_admin_path(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.put(
            f"{USERS}/{normal_user.id}/flags/can_add_part",
            headers=auth_headers(normal_user),
            json={"value": True},
        )
        assert resp.status_code == 403

    def test_admin_grant_unknown_user_404(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.put(
            f"{USERS}/{uuid.uuid4()}/flags/can_add_part",
            headers=auth_headers(admin_user),
            json={"value": True},
        )
        assert resp.status_code == 404


class TestHasCapability:
    def test_admin_override_and_grant(
        self,
        client: TestClient,
        db: Session,
        admin_user: User,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        # Maintainers/admins always pass without a grant.
        assert has_capability(db, admin_user, FlagKey.CAN_ADD_PART) is True
        # A plain user is denied until granted.
        assert has_capability(db, normal_user, FlagKey.CAN_ADD_PART) is False
        client.put(
            f"{USERS}/{normal_user.id}/flags/can_add_part",
            headers=auth_headers(admin_user),
            json={"value": True},
        )
        db.expire_all()
        assert has_capability(db, normal_user, FlagKey.CAN_ADD_PART) is True

    def test_get_flag_tristate(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        assert get_flag(db, normal_user.id, FlagKey.MAKER) is None
        client.put(f"{USERS}/me/flags/maker", headers=h, json={"value": True})
        db.expire_all()
        assert get_flag(db, normal_user.id, FlagKey.MAKER) is True
        client.put(f"{USERS}/me/flags/maker", headers=h, json={"value": False})
        db.expire_all()
        assert get_flag(db, normal_user.id, FlagKey.MAKER) is False
