"""Startup bootstrap: default admin (FR-007) and local dev seed data."""

import logging

from sqlalchemy.orm import Session

from app.auth.utils import hash_password
from app.config import settings
from app.database import SessionLocal
from app.users.constants import Locale, UserRole
from app.users.models import User

logger = logging.getLogger(__name__)


def _ensure_user(db: Session, username: str, password: str, role: UserRole) -> bool:
    """Create a user if the username is free. Returns True if created."""
    existing = db.query(User).filter(User.username == username).first()
    if existing is not None:
        return False
    db.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            preferred_locale=Locale.ES,
        )
    )
    return True


def bootstrap_admin(db: Session) -> None:
    """Create the default admin account on first run (FR-007)."""
    created = _ensure_user(
        db,
        settings.DEFAULT_ADMIN_USERNAME,
        settings.DEFAULT_ADMIN_PASSWORD,
        UserRole.ADMIN,
    )
    if created:
        db.commit()
        logger.info("Bootstrapped default admin '%s'", settings.DEFAULT_ADMIN_USERNAME)


def seed_dev_data(db: Session) -> None:
    """Seed a maintainer and a regular user for local development."""
    created_any = False
    created_any |= _ensure_user(
        db, "maintainer1", settings.SEED_DEV_PASSWORD, UserRole.MAINTAINER
    )
    created_any |= _ensure_user(db, "user1", settings.SEED_DEV_PASSWORD, UserRole.USER)
    if created_any:
        db.commit()
        logger.info("Seeded local development accounts (maintainer1, user1)")


def run_startup_bootstrap() -> None:
    """Run admin bootstrap and (optionally) dev seeding in one session."""
    db = SessionLocal()
    try:
        bootstrap_admin(db)
        if settings.SEED_DEV_DATA:
            seed_dev_data(db)
    finally:
        db.close()
