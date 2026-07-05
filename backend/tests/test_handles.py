"""Unit tests for the shared handle rules (``app/handles.py``)."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from app.handles import (
    HandleReservedError,
    InvalidHandleError,
    is_handle_taken,
    slugify_handle,
    unique_org_handle,
    validate_handle,
)
from app.users.models import User

MakeUser = Callable[..., User]


class TestValidateHandle:
    @pytest.mark.parametrize(
        "value",
        [
            "juan",
            "juan.carranza",
            "juan_perez",
            "red-cross",
            "a1b",
            "j.p_3-x",
            "  spaced  ",  # trimmed to "spaced"
        ],
    )
    def test_accepts_valid(self, value: str):
        assert validate_handle(value) == value.strip()

    @pytest.mark.parametrize(
        "value",
        [
            "ab",  # too short (< 3)
            "a" * 51,  # too long (> 50)
            "juan carranza",  # space
            "juan@perez",  # symbol
            "-juan",  # leading separator
            "juan-",  # trailing separator
            ".juan",  # leading dot
            "juan..perez",  # doubled separator
            "juan__x",  # doubled separator
            "juan-.x",  # adjacent separators
            "..",  # path traversal
            "niño",  # non-ASCII letter
        ],
    )
    def test_rejects_invalid_format(self, value: str):
        with pytest.raises(InvalidHandleError):
            validate_handle(value)

    @pytest.mark.parametrize("value", ["admin", "Login", "PARTS", "requests"])
    def test_rejects_reserved(self, value: str):
        with pytest.raises(HandleReservedError):
            validate_handle(value)

    def test_org_never_reserves_bare_org(self):
        assert validate_handle("org") == "org"

    def test_custom_error_code(self):
        with pytest.raises(InvalidHandleError) as exc:
            validate_handle("a b", error_code="INVALID_ORG_HANDLE")
        assert exc.value.error_code == "INVALID_ORG_HANDLE"


class TestIsHandleTaken:
    def test_matches_username_case_insensitively(
        self, db: Session, make_user: MakeUser
    ):
        make_user("Maria")
        assert is_handle_taken(db, "maria") is True
        assert is_handle_taken(db, "MARIA") is True
        assert is_handle_taken(db, "other") is False

    def test_excludes_self(self, db: Session, make_user: MakeUser):
        user = make_user("keepme")
        assert is_handle_taken(db, "keepme", exclude_user_id=user.id) is False


class TestSlugify:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Cruz Roja Venezolana", "cruz-roja-venezolana"),
            ("cruz roja", "cruz-roja"),
            ("  Fundación Niños  ", "fundacion-ninos"),
            ("UCAB Lab 3D", "ucab-lab-3d"),
            ("!!!", "org"),
            ("AB", "ab-org"),  # padded to satisfy the 3-char minimum
        ],
    )
    def test_slugify(self, name: str, expected: str):
        assert slugify_handle(name) == expected


class TestUniqueOrgHandle:
    def test_suffixes_on_collision_with_username(
        self, db: Session, make_user: MakeUser
    ):
        make_user("cruz-roja")
        assert unique_org_handle(db, "Cruz Roja") == "cruz-roja-2"
