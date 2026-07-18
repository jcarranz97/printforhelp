"""Render notification emails from outbox rows.

Each queued ``NotificationEmailOutbox`` row becomes a ``multipart/alternative``
email: a plain-text fallback plus a styled HTML body (inlined CSS, no external
assets). For a comment or @mention it mimics the on-page comment card —
"{actor} {action} on {entity}", the entity title, and the comment itself — then
a "Ver …" button to the item. The subject carries the entity title so a mailbox
does not thread unrelated notifications together. All user-supplied text is
HTML-escaped before it enters the HTML part.
"""

import html as html_lib
import re
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.activity.models import Comment
from app.config import settings
from app.users.models import User

from . import models
from .constants import MENTION_PATTERN, NotificationCategory

_MENTION_RE = re.compile(MENTION_PATTERN)

# Palette mirrored from the frontend light theme (frontend/app/globals.css) so
# the email reads like the app. Emails cannot use CSS variables, so the tokens
# are inlined as hex.
_ACCENT = "#0d9488"  # --accent (teal-600): button fill
_ACCENT_STRONG = "#0f766e"  # --accent-strong (teal-700): links, @mentions
_FOREGROUND = "#1a1a1a"  # --foreground
_MUTED = "#6b7280"  # --muted
_CARD_BORDER = "#e5e7eb"  # --card-border
_PAGE_BG = "#f4f5f5"  # neutral frame behind the white card
_AVATAR_BG = "#ccfbf1"  # light teal, mirrors the on-page comment avatar

_MAX_COMMENT_CHARS = 600
_MONTHS_ES = (
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
)  # fmt: skip

# Entity noun (with article) used in the lead line and the button label.
_ENTITY_NOUN: dict[EntityType, str] = {
    EntityType.REQUEST: "la petición",
    EntityType.REQUEST_ITEM: "el ítem de la petición",
    EntityType.RESOURCE: "la pieza",
    EntityType.COLLECTION_CENTER: "el centro de acopio",
    EntityType.SHIPMENT: "el envío",
    EntityType.TRACKING_GROUP: "el seguimiento",
    EntityType.REQUEST_REVIEW: "la revisión",
}

# Per-category subject line. Every one carries ``{title}`` so a mailbox does not
# collapse notifications from different entities into one thread.
_SUBJECT: dict[NotificationCategory, str] = {
    NotificationCategory.MENTION: "{actor} te mencionó en «{title}»",
    NotificationCategory.COMMENT: "Nuevo comentario en «{title}»",
    NotificationCategory.STATUS_CHANGE: "Cambio de estado en «{title}»",
    NotificationCategory.ITEM_ADDED: "Nuevo ítem en «{title}»",
    NotificationCategory.TRACKING_UPDATE: "Avance de seguimiento en «{title}»",
    NotificationCategory.REQUEST_REVIEWED: "Tu campaña «{title}» fue revisada",
    NotificationCategory.REVIEW_QUEUE: "Campaña pendiente de revisión: «{title}»",
}

# The bold action phrase for the lead line ("{actor} <b>{action}</b> en …").
_ACTION: dict[NotificationCategory, str] = {
    NotificationCategory.MENTION: "te mencionó",
    NotificationCategory.COMMENT: "comentó",
    NotificationCategory.STATUS_CHANGE: "cambió el estado",
    NotificationCategory.ITEM_ADDED: "agregó un ítem",
    NotificationCategory.TRACKING_UPDATE: "publicó un avance",
    NotificationCategory.REQUEST_REVIEWED: "revisó tu campaña",
    NotificationCategory.REVIEW_QUEUE: "envió una campaña para revisión",
}


def render_notification_email(
    db: Session, row: models.NotificationEmailOutbox
) -> tuple[str, str, str]:
    """Build ``(subject, text_body, html_body)`` for one notification email."""
    category = NotificationCategory(row.category)
    actor = _actor_username(db, row.actor_user_id)
    title = row.payload.get("title", "") or "PrintForHelp"
    entity_type = _entity_type(row.entity_type)
    noun = _ENTITY_NOUN.get(entity_type) if entity_type else None
    comment = _comment(db, row.comment_id)
    # A free-text note carried on the notification (e.g. a tracking update's
    # message); shown in a card like a comment when there is no comment.
    note = row.payload.get("note") if comment is None else None

    subject = _SUBJECT[category].format(actor=actor, title=title)
    action = _ACTION[category]
    lead_noun = noun or "PrintForHelp"
    button = f"Ver {noun}" if noun else "Abrir en PrintForHelp"

    anchor = row.payload.get("anchor")
    if anchor is None and comment is not None:
        anchor = f"comment-{comment.id}"
    url = _absolute_url(row.payload.get("link", ""), anchor)
    manage_url = f"{settings.PUBLIC_APP_BASE_URL.rstrip('/')}/settings/notifications"

    ctx = _Ctx(
        actor=actor,
        action=action,
        lead_noun=lead_noun,
        title=title,
        comment=comment,
        note=note,
        url=url,
        button=button,
        manage_url=manage_url,
    )
    return subject, _text_body(ctx), _html_body(ctx)


class _Ctx:
    """Bundle of resolved values shared by the text and HTML renderers."""

    def __init__(
        self,
        *,
        actor: str,
        action: str,
        lead_noun: str,
        title: str,
        comment: Comment | None,
        note: str | None,
        url: str,
        button: str,
        manage_url: str,
    ) -> None:
        self.actor = actor
        self.action = action
        self.lead_noun = lead_noun
        self.title = title
        self.comment = comment
        self.note = note
        self.url = url
        self.button = button
        self.manage_url = manage_url


def _text_body(ctx: _Ctx) -> str:
    """The plain-text fallback part."""
    lines = [
        "Hola,",
        "",
        f"{ctx.actor} {ctx.action} en {ctx.lead_noun}: «{ctx.title}»",
    ]
    if ctx.comment is not None:
        body = _clip(ctx.comment.body)
        lines += ["", f"{ctx.actor} · {_format_dt(ctx.comment.created_at)}", body]
    elif ctx.note is not None:
        lines += ["", f"{ctx.actor}:", _clip(ctx.note)]
    lines += [
        "",
        f"{ctx.button}: {ctx.url}",
        "",
        "—",
        "¿Quieres cambiar con qué frecuencia recibes correos de PrintForHelp? "
        f"Haz clic aquí: {ctx.manage_url}",
    ]
    return "\n".join(lines)


def _html_body(ctx: _Ctx) -> str:
    """The styled HTML part (inlined CSS, hyperlinks, no external assets)."""
    actor = html_lib.escape(ctx.actor)
    action = html_lib.escape(ctx.action)
    lead_noun = html_lib.escape(ctx.lead_noun)
    title = html_lib.escape(ctx.title)
    url_attr = html_lib.escape(ctx.url, quote=True)
    manage_attr = html_lib.escape(ctx.manage_url, quote=True)
    button = html_lib.escape(ctx.button)

    lead = (
        f'<p style="margin:0 0 4px;font-size:15px;line-height:1.5;'
        f'color:{_FOREGROUND};">'
        f"{actor} <strong>{action}</strong> en {lead_noun}:</p>"
    )
    title_block = (
        f'<p style="margin:0 0 16px;font-size:16px;font-weight:600;'
        f'color:{_FOREGROUND};">«{title}»</p>'
    )
    if ctx.comment is not None:
        card = _comment_card_html(actor, ctx.comment)
    elif ctx.note is not None:
        card = _note_card_html(actor, ctx.note)
    else:
        card = ""
    return f"""\
<div style="margin:0;padding:24px 0;background:{_PAGE_BG};">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border:1px solid \
{_CARD_BORDER};border-radius:12px;overflow:hidden;font-family:-apple-system,\
Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
    <div style="padding:18px 24px;border-bottom:1px solid {_CARD_BORDER};\
font-size:16px;font-weight:700;color:{_FOREGROUND};">PrintForHelp</div>
    <div style="padding:24px;">
      {lead}
      {title_block}
      {card}
      <a href="{url_attr}" style="display:inline-block;margin-top:20px;\
background:{_ACCENT};color:#ffffff;text-decoration:none;padding:11px 20px;\
border-radius:8px;font-size:14px;font-weight:600;">{button}</a>
    </div>
    <div style="padding:16px 24px;border-top:1px solid {_CARD_BORDER};\
background:#fafaf9;font-size:12px;line-height:1.5;color:{_MUTED};">
      ¿Quieres cambiar con qué frecuencia recibes correos de PrintForHelp?
      <a href="{manage_attr}" style="color:{_ACCENT_STRONG};\
text-decoration:underline;">Haz clic aquí</a>.
    </div>
  </div>
</div>"""


def _comment_card_html(actor: str, comment: Comment) -> str:
    """A comment card mimicking the on-page one (avatar + meta + body)."""
    meta = f"{actor} · {_format_dt(comment.created_at)}"
    return _card_html(actor, meta, _comment_body_html(_clip(comment.body)))


def _note_card_html(actor: str, note: str) -> str:
    """A card for a free-text note (e.g. a tracking update), styled like a comment."""
    return _card_html(actor, actor, _comment_body_html(_clip(note)))


def _card_html(actor: str, meta: str, body_html: str) -> str:
    """The shared avatar + meta + body card used for comments and notes."""
    initial = actor[:1].upper() or "?"
    return f"""\
<div style="border:1px solid {_CARD_BORDER};border-radius:10px;padding:14px 16px;\
background:#ffffff;">
        <div style="display:flex;align-items:center;margin-bottom:8px;">
          <span style="display:inline-block;width:26px;height:26px;line-height:26px;\
text-align:center;border-radius:50%;background:{_AVATAR_BG};color:{_ACCENT_STRONG};\
font-size:12px;font-weight:700;margin-right:8px;">{initial}</span>
          <span style="font-size:13px;color:{_MUTED};">{meta}</span>
        </div>
        <div style="font-size:14px;line-height:1.5;color:{_FOREGROUND};">\
{body_html}</div>
      </div>"""


def _comment_body_html(body: str) -> str:
    """Escape a comment body, highlight @mentions, and keep line breaks."""
    escaped = html_lib.escape(body)
    highlighted = _MENTION_RE.sub(
        lambda m: f'<strong style="color:{_ACCENT_STRONG};">{m.group(0)}</strong>',
        escaped,
    )
    return highlighted.replace("\n", "<br>")


def _clip(body: str) -> str:
    """Trim a very long comment so the email stays reasonable."""
    if len(body) <= _MAX_COMMENT_CHARS:
        return body
    return body[:_MAX_COMMENT_CHARS].rstrip() + "…"


def _format_dt(dt: datetime) -> str:
    """Format a timestamp as e.g. ``17 jul 2026, 17:23`` (UTC as stored)."""
    month = _MONTHS_ES[dt.month - 1]
    return f"{dt.day} {month} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"


def _entity_type(value: str) -> EntityType | None:
    """Parse the stored entity-type string, tolerating unknowns."""
    try:
        return EntityType(value)
    except ValueError:  # pragma: no cover - defensive; values come from the enum
        return None


def _comment(db: Session, comment_id: uuid.UUID | None) -> Comment | None:
    """Load the comment behind a notification, if it still exists."""
    if comment_id is None:
        return None
    return db.query(Comment).filter(Comment.id == comment_id).first()


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
