"""Shared pytest fixtures.

Tests run against a real PostgreSQL (the URL comes from ``DATABASE_URL``).
Each test gets a fresh schema via ``create_all`` / ``drop_all``. The
``client`` fixture deliberately does not enter the app lifespan, so the
startup admin bootstrap does not run during tests.
"""

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.activity.models
import app.audit_log.models
import app.collection_centers.models
import app.contributions.models
import app.notices.models
import app.notifications.models
import app.organizations.models
import app.requests.models
import app.resources.models
import app.shipments.models
import app.tracking.models
import app.users.models
from app.auth.service import create_access_token
from app.auth.utils import hash_password
from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base
from app.users.constants import Locale, UserRole
from app.users.models import User

test_engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

DEFAULT_TEST_PASSWORD = "Password123"


@pytest.fixture
def db() -> Generator[Session]:
    """Provide a clean database session for a single test.

    Drops any pre-existing tables first so the suite is deterministic even
    when the target database already holds rows (e.g. the local dev DB the
    backend container seeds on startup via ``SEED_DEV_DATA``).
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db: Session) -> Generator[TestClient]:
    """Return a TestClient with the DB dependency overridden."""
    app.dependency_overrides[get_db] = lambda: db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    """Factory fixture to create users directly in the database."""

    def _make(
        username: str,
        role: UserRole = UserRole.USER,
        password: str = DEFAULT_TEST_PASSWORD,
        active: bool = True,
    ) -> User:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            preferred_locale=Locale.ES,
            active=active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def admin_user(make_user: Callable[..., User]) -> User:
    """A single active admin account."""
    return make_user("admin", UserRole.ADMIN)


@pytest.fixture
def normal_user(make_user: Callable[..., User]) -> User:
    """A single active regular user account."""
    return make_user("user1", UserRole.USER)


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    """Factory returning Authorization headers for a given user."""

    def _headers(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return _headers
