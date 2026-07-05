"""User account business logic (admin provisioning + role management)."""

import re
import secrets
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.audit_log.constants import AuditAction, AuditTargetType
from app.audit_log.service import write_audit
from app.auth.exceptions import (
    InactiveUserExceptionError,
    InvalidGoogleTokenExceptionError,
)
from app.auth.google import verify_google_id_token
from app.auth.service import validate_password_strength
from app.auth.utils import hash_password
from app.handles import (
    HANDLE_MAX_LENGTH,
    HANDLE_MIN_LENGTH,
    RESERVED_HANDLES,
    is_handle_taken,
    validate_handle,
)

from . import models, schemas
from .constants import ANONYMOUS_USERNAME, Locale, UserRole
from .exceptions import (
    EmailTakenExceptionError,
    FlagNotSelfAssignableExceptionError,
    LockoutProtectionExceptionError,
    UnknownFlagExceptionError,
    UsernameAlreadyChosenExceptionError,
    UsernameTakenExceptionError,
    UserNotFoundExceptionError,
)
from .flags import FLAG_REGISTRY, FlagKey, FlagSource


def get_user_by_id_or_raise(db: Session, user_id: UUID) -> models.User:
    """Return a user by id or raise ``UserNotFoundExceptionError``."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise UserNotFoundExceptionError(user_id)
    return user


# ---------------------------------------------------------------------------
# Per-user flags (generic traits + capabilities; see ``flags.py``)
# ---------------------------------------------------------------------------


def _parse_flag_key(key: str) -> FlagKey:
    """Return the registered ``FlagKey`` for a raw key, or raise 422."""
    try:
        flag_key = FlagKey(key)
    except ValueError:
        raise UnknownFlagExceptionError(key) from None
    if flag_key not in FLAG_REGISTRY:  # pragma: no cover - registry covers enum
        raise UnknownFlagExceptionError(key)
    return flag_key


def get_user_flags(db: Session, user_id: UUID) -> dict[str, bool]:
    """Return the user's answered/granted flags as ``{key: value}``.

    Only active rows are returned; an absent key means "unknown".
    """
    rows = (
        db.query(models.UserFlag)
        .filter(
            models.UserFlag.user_id == user_id,
            models.UserFlag.active.is_(True),
        )
        .all()
    )
    return {row.key: row.value for row in rows}


def get_flag(db: Session, user_id: UUID, key: FlagKey) -> bool | None:
    """Return a single flag's tri-state value (True/False/None=unknown)."""
    row = (
        db.query(models.UserFlag)
        .filter(
            models.UserFlag.user_id == user_id,
            models.UserFlag.key == key.value,
            models.UserFlag.active.is_(True),
        )
        .first()
    )
    return row.value if row is not None else None


def _upsert_flag(
    db: Session,
    *,
    user_id: UUID,
    key: FlagKey,
    value: bool,
    source: FlagSource,
    set_by_id: UUID | None,
) -> models.UserFlag:
    """Insert or update the ``(user_id, key)`` flag row and commit."""
    row = (
        db.query(models.UserFlag)
        .filter(
            models.UserFlag.user_id == user_id,
            models.UserFlag.key == key.value,
        )
        .first()
    )
    if row is None:
        row = models.UserFlag(
            user_id=user_id,
            key=key.value,
            value=value,
            source=source.value,
            set_by_id=set_by_id,
        )
        db.add(row)
    else:
        row.value = value
        row.source = source.value
        row.set_by_id = set_by_id
        row.active = True
    db.commit()
    db.refresh(row)
    return row


def set_own_flag(
    db: Session, user: models.User, key: str, value: bool
) -> dict[str, bool]:
    """Let a user set one of their own self-assignable flags (e.g. ``maker``).

    Rejects flags that only admins may grant (``FLAG_NOT_SELF_ASSIGNABLE``).
    """
    flag_key = _parse_flag_key(key)
    if not FLAG_REGISTRY[flag_key].self_assignable:
        raise FlagNotSelfAssignableExceptionError(key)
    _upsert_flag(
        db,
        user_id=user.id,
        key=flag_key,
        value=value,
        source=FlagSource.SELF,
        set_by_id=user.id,
    )
    return get_user_flags(db, user.id)


def set_flag_as_admin(
    db: Session, target_user_id: UUID, key: str, value: bool, admin: models.User
) -> dict[str, bool]:
    """Grant or revoke any registered flag on a user (admin path)."""
    flag_key = _parse_flag_key(key)
    target = get_user_by_id_or_raise(db, target_user_id)
    _upsert_flag(
        db,
        user_id=target.id,
        key=flag_key,
        value=value,
        source=FlagSource.ADMIN,
        set_by_id=admin.id,
    )
    return get_user_flags(db, target.id)


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


def validate_new_username(
    db: Session, raw_username: str, *, exclude_user_id: UUID | None = None
) -> str:
    """Validate and reserve a username for a create/rename.

    Enforces the shared URL-safe handle rules (format, length, reserved
    words) and cross-namespace uniqueness — a username may not collide with
    another user *or* an organization handle, since both share the
    ``/{handle}`` profile-URL namespace. Returns the cleaned username or
    raises ``INVALID_USERNAME`` / ``USERNAME_RESERVED`` / ``USERNAME_TAKEN``.
    """
    username = validate_handle(raw_username, error_code="INVALID_USERNAME")
    if is_handle_taken(db, username, exclude_user_id=exclude_user_id):
        raise UsernameTakenExceptionError(username)
    return username


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
    username = validate_new_username(db, payload.username)
    email = payload.email.strip().lower()
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


def _unique_username_from_email(db: Session, email: str) -> str:
    """Build a unique username from an email's local part.

    Keeps only safe characters and appends a number if the name is taken,
    so Google sign-ups get a sensible, collision-free username.
    """
    local_part = email.split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9._-]", "", local_part)
    # Collapse any run of separators to its first char and trim the edges so
    # the result satisfies the URL-safe handle rules (no leading/trailing or
    # doubled ``. _ -``).
    base = re.sub(r"([._-])[._-]+", r"\1", base).strip("._-")
    # Leave room for a numeric suffix; re-trim in case the slice ended on a
    # separator.
    base = base[: HANDLE_MAX_LENGTH - 4].strip("._-")
    if len(base) < HANDLE_MIN_LENGTH:
        base = "user"
    candidate = base
    suffix = 1
    while candidate.lower() in RESERVED_HANDLES or is_handle_taken(db, candidate):
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def login_or_create_google_user(db: Session, id_token: str) -> models.User:
    """Sign a user in with Google, creating the account on first login.

    Verifies the Google id_token, then either returns the existing account
    for that email (linking its ``google_sub`` if not set yet) or provisions
    a brand-new ``user`` account from the Google profile. The email must be
    Google-verified; the created account gets an unusable random password
    (it only ever logs in through Google).
    """
    claims = verify_google_id_token(id_token)
    email = str(claims.get("email") or "").strip().lower()
    sub = str(claims.get("sub") or "")
    if not email or claims.get("email_verified") is not True or not sub:
        raise InvalidGoogleTokenExceptionError

    user = get_user_by_email(db, email)
    if user is not None:
        if not user.active:
            raise InactiveUserExceptionError
        if user.google_sub is None:
            user.google_sub = sub
            db.commit()
            db.refresh(user)
        return user

    full_name = str(claims.get("name") or "").strip() or None
    user = models.User(
        username=_unique_username_from_email(db, email),
        email=email,
        full_name=full_name,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        google_sub=sub,
        role=UserRole.USER,
        preferred_locale=Locale.ES,
        # Auto-generated username; the user must pick their own on first login.
        username_chosen=False,
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


def set_own_username(db: Session, user: models.User, new_username: str) -> models.User:
    """Let a Google user pick their username on first login (one-time).

    Only allowed while ``username_chosen`` is False (freshly-created Google
    accounts). The chosen name goes through the shared handle rules
    (format, reserved words, cross-namespace uniqueness) via
    ``validate_new_username``.
    """
    if user.username_chosen:
        raise UsernameAlreadyChosenExceptionError

    username = validate_new_username(db, new_username, exclude_user_id=user.id)
    user.username = username
    user.username_chosen = True
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
    username = validate_new_username(db, payload.username)
    validate_password_strength(payload.password)

    user = models.User(
        username=username,
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
