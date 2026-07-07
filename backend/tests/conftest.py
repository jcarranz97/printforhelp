"""Shared pytest fixtures.

Tests run against a real PostgreSQL, but **never** against the dev/prod
``DATABASE_URL`` — each test drops and recreates every table, which would wipe
a running local environment. The suite therefore uses a dedicated *test*
database (see :func:`_resolve_test_database_url`): ``settings.TEST_DATABASE_URL``
when set (CI does this), otherwise a ``<db>_test`` database derived from
``DATABASE_URL`` and auto-created if it does not exist yet.

Each test gets a fresh schema via ``create_all`` / ``drop_all``. The ``client``
fixture deliberately does not enter the app lifespan, so the startup admin
bootstrap does not run during tests.
"""

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import app.activity.models
import app.audit_log.models
import app.auth.models
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
from app.database import SessionLocal, get_db
from app.main import app
from app.models import Base
from app.ratelimit import limiter
from app.users.constants import Locale, UserRole
from app.users.models import User

# Rate limiting is off during the suite so functional tests are not
# throttled; the dedicated rate-limit test re-enables it explicitly.
limiter.enabled = False


def _resolve_test_database_url() -> str:
    """Return the URL of the dedicated test database (never the dev DB).

    Uses ``settings.TEST_DATABASE_URL`` when set; otherwise derives a
    ``<db>_test`` sibling of ``DATABASE_URL`` so a local run can never touch
    the developer's live database. Guards against the two being identical.
    """
    if settings.TEST_DATABASE_URL:
        url = make_url(settings.TEST_DATABASE_URL)
    else:
        dev = make_url(settings.DATABASE_URL)
        url = dev.set(database=f"{dev.database or 'printforhelp'}_test")
    if url.render_as_string(hide_password=False) == settings.DATABASE_URL:
        raise RuntimeError(
            "The test database must differ from DATABASE_URL: the suite drops "
            "every table. Set TEST_DATABASE_URL to a separate database."
        )
    return url.render_as_string(hide_password=False)


def _ensure_database_exists(url_str: str) -> None:
    """Create the target database if it is missing (idempotent).

    Connects to the server's ``postgres`` maintenance database so the CREATE
    runs outside the target; a no-op when the database already exists.
    """
    url = make_url(url_str)
    maintenance = url.set(database="postgres")
    engine = create_engine(
        maintenance.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        engine.dispose()


TEST_DATABASE_URL = _resolve_test_database_url()
_ensure_database_exists(TEST_DATABASE_URL)
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

# Most tests inject the DB via the ``get_db`` override, but some app paths open
# their own session straight from ``app.database.SessionLocal`` (e.g. the
# scheduled expire-claims job). Rebind that factory onto the test engine so
# those paths also hit the test database, not the real ``DATABASE_URL``.
SessionLocal.configure(bind=test_engine)

DEFAULT_TEST_PASSWORD = "Password123"


@pytest.fixture
def db() -> Generator[Session]:
    """Provide a clean database session for a single test.

    Runs against the dedicated test database (see the module docstring), not
    the dev ``DATABASE_URL``. Drops any pre-existing tables first so the suite
    is deterministic even if a previous run left rows behind.
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
