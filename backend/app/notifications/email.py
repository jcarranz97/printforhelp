"""Render notification emails from outbox rows.

Plain-text Spanish emails (matching the existing password-reset email),
one per queued ``NotificationEmailOutbox`` row. Every footer carries three
links: a one-click "stop following this" (for watch-based categories), a
one-click "stop emailing me this category", and a general link to the full
preference center. The first two are signed, no-login unsubscribe tokens
(see :mod:`app.notifications.unsubscribe`); the third just deep-links to
``/settings/notifications``.
"""

import uuid

from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.config import settings
from app.users.models import User

from . import models
from .constants import NotificationCategory
from .unsubscribe import (
    CATEGORY_LABELS_ES,
    email_action,
    make_unsubscribe_token,
    unwatch_action,
)

# Per-category subject + opening line. ``{actor}`` is the triggering user's
# username and ``{title}`` the entity's display title.
_COPY: dict[NotificationCategory, tuple[str, str]] = {
    NotificationCategory.MENTION: (
        "{actor} te mencionó en PrintForHelp",
        "{actor} te mencionó en un comentario en «{title}».",
    ),
    NotificationCategory.COMMENT: (
        "Nuevo comentario en «{title}»",
        "{actor} comentó en «{title}», que sigues.",
    ),
    NotificationCategory.STATUS_CHANGE: (
        "Cambio de estado en «{title}»",
        "{actor} cambió el estado de «{title}», que sigues.",
    ),
    NotificationCategory.ITEM_ADDED: (
        "Nuevo ítem en «{title}»",
        "{actor} agregó un nuevo ítem a la campaña «{title}», que sigues.",
    ),
    NotificationCategory.TRACKING_UPDATE: (
        "Avance de seguimiento en «{title}»",
        "Hay un nuevo avance en el seguimiento de «{title}».",
    ),
    NotificationCategory.REQUEST_REVIEWED: (
        "Tu campaña «{title}» fue revisada",
        "Tu campaña «{title}» fue revisada. Abre PrintForHelp para ver el resultado.",
    ),
    NotificationCategory.REVIEW_QUEUE: (
        "Campaña pendiente de revisión: «{title}»",
        "{actor} envió la campaña «{title}» para revisión.",
    ),
}

# Categories notified by role rather than by a subscription; a "stop
# following this" link is meaningless for them, so the footer omits it.
_NO_UNWATCH_CATEGORIES = frozenset(
    {NotificationCategory.REQUEST_REVIEWED, NotificationCategory.REVIEW_QUEUE}
)


def render_notification_email(
    db: Session, row: models.NotificationEmailOutbox
) -> tuple[str, str]:
    """Build the ``(subject, body)`` for one queued notification email."""
    category = NotificationCategory(row.category)
    actor = _actor_username(db, row.actor_user_id)
    title = row.payload.get("title", "") or "PrintForHelp"
    subject_tpl, intro_tpl = _COPY[category]
    subject = subject_tpl.format(actor=actor, title=title)
    intro = intro_tpl.format(actor=actor, title=title)
    url = _absolute_url(row.payload.get("link", ""), row.payload.get("anchor"))
    footer = _footer(row, category)
    body = f"Hola,\n\n{intro}\n\nÁbrelo aquí:\n{url}\n\n{footer}"
    return subject, body


def _actor_username(db: Session, actor_user_id: uuid.UUID) -> str:
    """Return the actor's username, or a neutral fallback if since removed."""
    username = db.query(User.username).filter(User.id == actor_user_id).scalar()
    return username or "Alguien"


def _absolute_url(link: str, anchor: str | None) -> str:
    """Turn a stored relative ``link`` (+ optional anchor) into an absolute URL."""
    base = settings.PUBLIC_APP_BASE_URL.rstrip("/")
    url = f"{base}{link}" if link.startswith("/") else f"{base}/{link}"
    if anchor and "#" not in link:
        url = f"{url}#{anchor}"
    return url


def _footer(row: models.NotificationEmailOutbox, category: NotificationCategory) -> str:
    """Build the three-link Spanish unsubscribe/preferences footer."""
    base = settings.PUBLIC_APP_BASE_URL.rstrip("/")
    lines = ["—", "PrintForHelp"]
    if category not in _NO_UNWATCH_CATEGORIES:
        token = make_unsubscribe_token(
            row.recipient_user_id,
            unwatch_action(EntityType(row.entity_type), row.entity_id),
        )
        lines.append(f"Dejar de seguir esto: {base}/unsubscribe?token={token}")
    email_token = make_unsubscribe_token(row.recipient_user_id, email_action(category))
    label = CATEGORY_LABELS_ES.get(category, category.value)
    lines.append(
        f"Dejar de recibir correos de «{label}»: {base}/unsubscribe?token={email_token}"
    )
    lines.append(
        "¿Quieres cambiar con qué frecuencia recibes correos de PrintForHelp? "
        f"Haz clic aquí: {base}/settings/notifications"
    )
    return "\n".join(lines)
