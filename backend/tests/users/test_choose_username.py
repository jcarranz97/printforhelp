"""Tests for the one-time username choice (Google onboarding)."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.users.models import User, UsernameChange

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

    def test_established_account_can_rename_once(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        """Renaming is allowed, then blocked by the cooldown until it lapses."""
        headers = auth_headers(normal_user)
        resp = client.put(URL, headers=headers, json={"username": "newname"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["username"] == "newname"
        # The cooldown is reported so the UI can lock the field.
        assert (
            client.get(ME, headers=headers).json()["username_change_available_at"]
            is not None
        )

        again = client.put(URL, headers=headers, json={"username": "thirdname"})
        assert again.status_code == 409
        assert again.json()["error"]["code"] == "USERNAME_CHANGE_TOO_SOON"
        # ...and the handle really did not move.
        assert client.get(ME, headers=headers).json()["username"] == "newname"

    def test_rename_is_recorded_in_history(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        client.put(URL, headers=auth_headers(normal_user), json={"username": "renamed"})
        change = (
            db.query(UsernameChange)
            .filter(UsernameChange.user_id == normal_user.id)
            .one()
        )
        assert (change.from_username, change.to_username) == ("user1", "renamed")

    def test_renaming_to_the_same_name_is_a_no_op(
        self,
        client: TestClient,
        db: Session,
        normal_user: User,
        auth_headers: Callable[[User], dict[str, str]],
    ):
        """Re-submitting the current name must not burn the cooldown."""
        headers = auth_headers(normal_user)
        resp = client.put(URL, headers=headers, json={"username": "user1"})
        assert resp.status_code == 200
        assert (
            db.query(UsernameChange)
            .filter(UsernameChange.user_id == normal_user.id)
            .count()
            == 0
        )
        assert (
            client.get(ME, headers=headers).json()["username_change_available_at"]
            is None
        )

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
        for bad in ("ab", "has space", "tilde~", "", "-lead", "dup..dot"):
            resp = client.put(URL, headers=headers, json={"username": bad})
            assert resp.status_code == 422

    def test_dotted_username_is_accepted(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        user = _pending_user(db, make_user)
        resp = client.put(
            URL, headers=auth_headers(user), json={"username": "juan.carranza"}
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "juan.carranza"

    def test_reserved_username_is_rejected(
        self,
        client: TestClient,
        db: Session,
        make_user: Callable[..., User],
        auth_headers: Callable[[User], dict[str, str]],
    ):
        user = _pending_user(db, make_user)
        resp = client.put(URL, headers=auth_headers(user), json={"username": "admin"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "USERNAME_RESERVED"
