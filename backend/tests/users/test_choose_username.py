"""Tests for the one-time username choice (Google onboarding)."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.users.models import User

URL = "/api/v1/users/me/username"
ME = "/api/v1/auth/me"


def _pending_user(
    db: Session, make_user: Callable[..., User], username: str = "tempname"
) -> User:
    """A user that still needs to choose a username (like a Google sign-up)."""
    user = make_user(username)
    user.username_chosen = False
    db.commit()
    db.refresh(user)
    return user


class TestChooseUsername:
    def test_requires_auth(self, client: TestClient):
        assert client.put(URL, json={"username": "whatever"}).status_code == 401

    def test_pick_username_success(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        user = _pending_user(db, make_user)
        resp = client.put(
            URL, headers=auth_headers(user), json={"username": "cooljose"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "cooljose"
        assert body["username_chosen"] is True
        me = client.get(ME, headers=auth_headers(user)).json()
        assert me["username"] == "cooljose"
        assert me["username_chosen"] is True

    def test_already_chosen_is_rejected(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        # A normal account already has username_chosen=True.
        resp = client.put(
            URL, headers=auth_headers(normal_user), json={"username": "newname"}
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_ALREADY_SET"

    def test_taken_username_is_rejected(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        make_user("occupied")
        user = _pending_user(db, make_user)
        resp = client.put(
            URL, headers=auth_headers(user), json={"username": "occupied"}
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_TAKEN"

    def test_taken_is_case_insensitive(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        make_user("Occupied")
        user = _pending_user(db, make_user)
        resp = client.put(
            URL, headers=auth_headers(user), json={"username": "OCCUPIED"}
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_TAKEN"

    def test_bad_format_is_rejected(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        user = _pending_user(db, make_user)
        headers = auth_headers(user)
        for bad in ("ab", "has space", "tilde~", ""):
            resp = client.put(URL, headers=headers, json={"username": bad})
            assert resp.status_code == 422
