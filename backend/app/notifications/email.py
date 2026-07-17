"""Render notification emails from outbox rows.

Each queued ``NotificationEmailOutbox`` row becomes a small, self-contained
email with two parts: a plain-text fallback and a styled HTML body (inlined
CSS, no external assets, so it renders anywhere). Both carry a call-to-action
link to the notification's target and a single footer line linking to the
preference center, where the recipient controls every channel. All
user-supplied text is HTML-escaped before it goes into the HTML part.
"""

import html as html_lib
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.users.models import User

from . import models
from .constants import NotificationCategory

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
        "Tu campaña «{title}» fue revisada. Ábrela en PrintForHelp para ver el "
        "resultado.",
    ),
    NotificationCategory.REVIEW_QUEUE: (
        "Campaña pendiente de revisión: «{title}»",
        "{actor} envió la campaña «{title}» para revisión.",
    ),
}

_CTA = "Abrir en PrintForHelp"
_ACCENT = "#2563eb"


def render_notification_email(
    db: Session, row: models.NotificationEmailOutbox
) -> tuple[str, str, str]:
    """Build ``(subject, text_body, html_body)`` for one notification email."""
    category = NotificationCategory(row.category)
    actor = _actor_username(db, row.actor_user_id)
    title = row.payload.get("title", "") or "PrintForHelp"
    subject_tpl, intro_tpl = _COPY[category]
    subject = subject_tpl.format(actor=actor, title=title)
    intro = intro_tpl.format(actor=actor, title=title)
    url = _absolute_url(row.payload.get("link", ""), row.payload.get("anchor"))
    base = settings.PUBLIC_APP_BASE_URL.rstrip("/")
    manage_url = f"{base}/settings/notifications"
    text = _text_body(intro, url, manage_url)
    html = _html_body(intro, url, manage_url)
    return subject, text, html


def _text_body(intro: str, url: str, manage_url: str) -> str:
    """The plain-text fallback part."""
    return (
        f"Hola,\n\n{intro}\n\n"
        f"Ábrelo aquí:\n{url}\n\n"
        "—\n"
        "¿Quieres cambiar con qué frecuencia recibes correos de PrintForHelp? "
        f"Haz clic aquí: {manage_url}"
    )


def _html_body(intro: str, url: str, manage_url: str) -> str:
    """The styled HTML part (inlined CSS, hyperlinks, no external assets)."""
    intro_html = html_lib.escape(intro)
    url_attr = html_lib.escape(url, quote=True)
    manage_attr = html_lib.escape(manage_url, quote=True)
    return f"""\
<div style="margin:0;padding:24px 0;background:#f4f4f5;">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border:1px solid \
#e4e4e7;border-radius:12px;overflow:hidden;font-family:-apple-system,Segoe UI,\
Roboto,Helvetica,Arial,sans-serif;">
    <div style="padding:18px 24px;border-bottom:1px solid #f0f0f0;\
font-size:16px;font-weight:700;color:#111827;">PrintForHelp</div>
    <div style="padding:24px;">
      <p style="margin:0 0 20px;font-size:15px;line-height:1.5;color:#111827;">\
{intro_html}</p>
      <a href="{url_attr}" style="display:inline-block;background:{_ACCENT};\
color:#ffffff;text-decoration:none;padding:11px 20px;border-radius:8px;\
font-size:14px;font-weight:600;">{_CTA}</a>
    </div>
    <div style="padding:16px 24px;border-top:1px solid #f0f0f0;background:#fafafa;\
font-size:12px;line-height:1.5;color:#6b7280;">
      ¿Quieres cambiar con qué frecuencia recibes correos de PrintForHelp?
      <a href="{manage_attr}" style="color:{_ACCENT};text-decoration:underline;">\
Haz clic aquí</a>.
    </div>
  </div>
</div>"""


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
