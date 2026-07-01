"""User account business logic (admin provisioning + role management)."""

import secrets
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.auth.service import validate_password_strength
from app.auth.utils import hash_password

from . import models, schemas
from .constants import ANONYMOUS_USERNAME, Locale, UserRole
from .exceptions import (
    EmailTakenExceptionError,
    LockoutProtectionExceptionError,
    UsernameTakenExceptionError,
    UserNotFoundExceptionError,
)


def get_user_by_id_or_raise(db: Session, user_id: UUID) -> models.User:
    """Return a user by id or raise ``UserNotFoundExceptionError``."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise UserNotFoundExceptionError(user_id)
    return user


def get_user_by_username(db: Session, username: str) -> models.User | None:
    """Return a user by username (case-insensitive), or None.

    Usernames are stored with their original case for display, but
    looked up case-insensitively so "Maria" and "maria" are the same
    account for both duplicate checks and login.
    """
    return (
        db.query(models.User)
        .filter(func.lower(models.User.username) == username.lower())
        .first()
    )


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Return a user by email (case-insensitive), or None."""
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email.lower())
        .first()
    )


def register_user(db: Session, payload: schemas.UserRegister) -> models.User:
    """Self-register a new account from name + username + email + password.

    Both the username and the (lowercased) email must be unique; either
    can later be used as the login identifier. New accounts always get the
    default ``user`` role and Spanish locale; email verification is
    intentionally not required in v1 (FR-001).
    """
    username = payload.username.strip()
    email = payload.email.strip().lower()
    if get_user_by_username(db, username) is not None:
        raise UsernameTakenExceptionError(username)
    if get_user_by_email(db, email) is not None:
        raise EmailTakenExceptionError(email)
    validate_password_strength(payload.password)

    user = models.User(
        username=username,
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
        preferred_locale=Locale.ES,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        user.id,
        AuditAction.SELF_REGISTER,
        AuditTargetType.USER,
        user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def get_or_create_anonymous_user(db: Session) -> models.User:
    """Return the system ``anonymous`` account, creating it if absent.

    This account owns assets submitted without logging in (e.g. a
    collection center registered by a guest). It is given an unguessable
    password and is never meant to authenticate; maintainers moderate the
    centers it owns. Idempotent and safe to call on every anonymous submit.
    """
    user = get_user_by_username(db, ANONYMOUS_USERNAME)
    if user is not None:
        return user
    user = models.User(
        username=ANONYMOUS_USERNAME,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role=UserRole.USER,
        preferred_locale=Locale.ES,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[models.User]:
    """List all users, newest first (admin only)."""
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


def search_users(db: Session, query: str, limit: int) -> list[models.User]:
    """Prefix-search active users by username or full name (for @mentions).

    Powers the comment @mention typeahead. The system ``anonymous`` account
    is never a valid mention target and is excluded. An empty query returns
    the first ``limit`` users so the menu can show suggestions the instant
    ``@`` is typed.
    """
    q = db.query(models.User).filter(
        models.User.active.is_(True),
        models.User.username != ANONYMOUS_USERNAME,
    )
    term = query.strip().lower()
    if term:
        like = f"{term}%"
        q = q.filter(
            or_(
                func.lower(models.User.username).like(like),
                func.lower(models.User.full_name).like(like),
            )
        )
    return q.order_by(models.User.username).limit(limit).all()


def create_user(
    db: Session, payload: schemas.UserCreate, actor: models.User
) -> models.User:
    """Admin-provision a new account (FR-007 / Phase 1)."""
    if get_user_by_username(db, payload.username) is not None:
        raise UsernameTakenExceptionError(payload.username)
    validate_password_strength(payload.password)

    user = models.User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        preferred_locale=payload.preferred_locale,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        actor.id,
        AuditAction.CREATE_USER,
        AuditTargetType.USER,
        user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def _count_active_admins(db: Session) -> int:
    return (
        db.query(models.User)
        .filter(
            models.User.role == UserRole.ADMIN,
            models.User.active.is_(True),
        )
        .count()
    )


def _assert_not_last_active_admin(db: Session, target: models.User) -> None:
    """Guard against demoting/deactivating the last active admin (FR-014)."""
    if (
        target.role == UserRole.ADMIN
        and target.active
        and _count_active_admins(db) <= 1
    ):
        raise LockoutProtectionExceptionError


def update_role(
    db: Session, user_id: UUID, new_role: UserRole, actor: models.User
) -> models.User:
    """Change a user's role (admin only, FR-010 / FR-014)."""
    user = get_user_by_id_or_raise(db, user_id)
    if new_role != UserRole.ADMIN:
        _assert_not_last_active_admin(db, user)

    user.role = new_role
    write_audit(
        db,
        actor.id,
        AuditAction.CHANGE_ROLE,
        AuditTargetType.USER,
        user.id,
        reason=f"role={new_role.value}",
    )
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: UUID, actor: models.User) -> models.User:
    """Soft-deactivate a user account (admin only, FR-012 / FR-014)."""
    user = get_user_by_id_or_raise(db, user_id)
    _assert_not_last_active_admin(db, user)

    user.active = False
    write_audit(
        db,
        actor.id,
        AuditAction.DEACTIVATE_USER,
        AuditTargetType.USER,
        user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def set_password(
    db: Session, user_id: UUID, new_password: str, actor: models.User
) -> models.User:
    """Admin-set a new password for any account (Phase 1).

    Unlike the self-service flow (FR-005), no current password is
    required; the password policy (FR-002) is still enforced.
    """
    user = get_user_by_id_or_raise(db, user_id)
    validate_password_strength(new_password)

    user.password_hash = hash_password(new_password)
    write_audit(
        db,
        actor.id,
        AuditAction.RESET_PASSWORD,
        AuditTargetType.USER,
        user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def reactivate_user(db: Session, user_id: UUID, actor: models.User) -> models.User:
    """Reactivate a previously deactivated account (admin only, FR-012)."""
    user = get_user_by_id_or_raise(db, user_id)

    user.active = True
    write_audit(
        db,
        actor.id,
        AuditAction.REACTIVATE_USER,
        AuditTargetType.USER,
        user.id,
    )
    db.commit()
    db.refresh(user)
    return user
