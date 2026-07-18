"""Signed, no-login unsubscribe links for notification emails.

Every notification email footer carries one-click links that must work
without the recipient signing in (they are reading their inbox, not the
app). Each link is a JWT signed with the app ``SECRET_KEY`` encoding the
user id and an *action*:

- ``email:<category>`` — stop emailing this category (flip its email pref
  off, leaving the in-app channel untouched).
- ``unwatch:<entity_type>:<entity_id>`` — stop following this entity.

The token carries no expiry: an unsubscribe link should keep working
however old the email is. It is single-purpose (``purpose = "unsubscribe"``)
so a leaked login JWT can't be replayed here and vice versa.
"""

import uuid

import jwt
from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.config import settings
from app.users.models import User

from . import models, service
from .constants import CATEGORY_DEFAULTS, NotificationCategory
from .exceptions import InvalidUnsubscribeTokenExceptionError

_PURPOSE = "unsubscribe"
_EMAIL_PREFIX = "email:"
_UNWATCH_PREFIX = "unwatch:"


def email_action(category: NotificationCategory) -> str:
    """Return the action string that turns a category's emails off."""
    return f"{_EMAIL_PREFIX}{category.value}"


def unwatch_action(entity_type: EntityType, entity_id: uuid.UUID) -> str:
    """Return the action string that unwatches an entity."""
    return f"{_UNWATCH_PREFIX}{entity_type.value}:{entity_id}"


def make_unsubscribe_token(user_id: uuid.UUID, action: str) -> str:
    """Sign a ``(user, action)`` unsubscribe token."""
    payload = {"sub": str(user_id), "act": action, "purpose": _PURPOSE}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def parse_unsubscribe_token(token: str) -> tuple[uuid.UUID, str]:
    """Verify a token and return ``(user_id, action)``; raise if invalid."""
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidUnsubscribeTokenExceptionError from exc
    if claims.get("purpose") != _PURPOSE:
        raise InvalidUnsubscribeTokenExceptionError
    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise InvalidUnsubscribeTokenExceptionError from exc
    action = claims.get("act")
    if not isinstance(action, str) or not action:
        raise InvalidUnsubscribeTokenExceptionError
    return user_id, action


def describe_action(db: Session, action: str) -> str:
    """A Spanish, human-readable summary of what confirming the link does."""
    if action.startswith(_EMAIL_PREFIX):
        category = _parse_category(action)
        label = CATEGORY_LABELS_ES.get(category, category.value)
        return f"Dejarás de recibir correos sobre: {label}."
    entity_type, entity_id = _parse_unwatch(action)
    title = service.entity_title(db, entity_type, entity_id)
    return f"Dejarás de seguir «{title}» y no recibirás más avisos suyos."


def apply_unsubscribe(db: Session, user_id: uuid.UUID, action: str) -> str:
    """Apply an unsubscribe action; return a Spanish confirmation summary.

    Raises :class:`InvalidUnsubscribeTokenExceptionError` for an unknown user
    or malformed action so a tampered link fails the same way a bad signature
    does (no information leak).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise InvalidUnsubscribeTokenExceptionError
    if action.startswith(_EMAIL_PREFIX):
        category = _parse_category(action)
        service.set_preference(
            db,
            user=user,
            category=category,
            in_app_enabled=_current_in_app(db, user_id, category),
            email_enabled=False,
        )
        label = CATEGORY_LABELS_ES.get(category, category.value)
        return f"Listo. Ya no recibirás correos sobre: {label}."
    entity_type, entity_id = _parse_unwatch(action)
    service.unwatch_entity(db, user=user, entity_type=entity_type, entity_id=entity_id)
    return "Listo. Dejaste de seguir este elemento."


def _parse_category(action: str) -> NotificationCategory:
    """Extract a valid category from an ``email:<category>`` action."""
    try:
        return NotificationCategory(action[len(_EMAIL_PREFIX) :])
    except ValueError as exc:
        raise InvalidUnsubscribeTokenExceptionError from exc


def _parse_unwatch(action: str) -> tuple[EntityType, uuid.UUID]:
    """Extract ``(entity_type, entity_id)`` from an ``unwatch:...`` action."""
    rest = action[len(_UNWATCH_PREFIX) :]
    entity_type_raw, _, entity_id_raw = rest.partition(":")
    try:
        return EntityType(entity_type_raw), uuid.UUID(entity_id_raw)
    except ValueError as exc:
        raise InvalidUnsubscribeTokenExceptionError from exc


def _current_in_app(
    db: Session, user_id: uuid.UUID, category: NotificationCategory
) -> bool:
    """Return the user's current in-app choice for a category (or its default)."""
    row = (
        db.query(models.NotificationPreference.in_app_enabled)
        .filter(
            models.NotificationPreference.user_id == user_id,
            models.NotificationPreference.category == category.value,
            models.NotificationPreference.active.is_(True),
        )
        .first()
    )
    if row is not None:
        return bool(row[0])
    return CATEGORY_DEFAULTS[category][0]


# Short Spanish labels for each category, reused in the email footer and the
# unsubscribe-confirmation copy. (User-facing email copy is Spanish, matching
# the existing password-reset email.)
CATEGORY_LABELS_ES: dict[NotificationCategory, str] = {
    NotificationCategory.MENTION: "menciones (@tu usuario)",
    NotificationCategory.COMMENT: "comentarios en lo que sigues",
    NotificationCategory.STATUS_CHANGE: "cambios de estado en lo que sigues",
    NotificationCategory.ITEM_ADDED: "nuevos ítems en campañas que sigues",
    NotificationCategory.TRACKING_UPDATE: "avances de seguimiento",
    NotificationCategory.REQUEST_REVIEWED: "la revisión de tu campaña",
    NotificationCategory.REVIEW_QUEUE: "campañas pendientes de revisión",
    NotificationCategory.REACTION: "reacciones a tus publicaciones y comentarios",
}
