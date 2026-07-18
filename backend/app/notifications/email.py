"""Render notification emails from outbox rows.

Each queued ``NotificationEmailOutbox`` row becomes a ``multipart/alternative``
email: a plain-text fallback plus a styled HTML body (inlined CSS, no external
assets). For a comment or @mention it mimics the on-page comment card —
"{actor} {action} on {entity}", the entity title, and the comment itself — then
a "View …" button to the item. The subject carries the entity title so a mailbox
does not thread unrelated notifications together.

Copy is localized to the recipient's ``preferred_locale`` (Spanish or English),
which the worker passes in. All user-supplied text is HTML-escaped before it
enters the HTML part.
"""

import html as html_lib
import re
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.activity.constants import EntityType
from app.activity.models import Comment
from app.config import settings
from app.users.constants import Locale
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
_MONTHS: dict[Locale, tuple[str, ...]] = {
    Locale.ES: (
        "ene", "feb", "mar", "abr", "may", "jun",
        "jul", "ago", "sep", "oct", "nov", "dic",
    ),
    Locale.EN: (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ),
}  # fmt: skip

# Entity noun (with article) used in the lead line and the button label.
_ENTITY_NOUN: dict[Locale, dict[EntityType, str]] = {
    Locale.ES: {
        EntityType.REQUEST: "la petición",
        EntityType.REQUEST_ITEM: "el ítem de la petición",
        EntityType.RESOURCE: "la pieza",
        EntityType.COLLECTION_CENTER: "el centro de acopio",
        EntityType.SHIPMENT: "el envío",
        EntityType.TRACKING_GROUP: "el seguimiento",
        EntityType.REQUEST_REVIEW: "la revisión",
        EntityType.COMMENT: "tu comentario",
    },
    Locale.EN: {
        EntityType.REQUEST: "the request",
        EntityType.REQUEST_ITEM: "the request item",
        EntityType.RESOURCE: "the part",
        EntityType.COLLECTION_CENTER: "the collection center",
        EntityType.SHIPMENT: "the shipment",
        EntityType.TRACKING_GROUP: "the tracking",
        EntityType.REQUEST_REVIEW: "the review",
        EntityType.COMMENT: "your comment",
    },
}

# Possessive noun used only in a reaction ("like") lead line, so it reads
# "liked your part" / "le gustó tu pieza" — matching the in-app copy — instead
# of the definite-article form ("the part") the other categories use.
_REACTION_NOUN: dict[Locale, dict[EntityType, str]] = {
    Locale.ES: {
        EntityType.REQUEST: "tu petición",
        EntityType.REQUEST_ITEM: "tu ítem",
        EntityType.RESOURCE: "tu pieza",
        EntityType.COLLECTION_CENTER: "tu centro de acopio",
        EntityType.SHIPMENT: "tu envío",
        EntityType.COMMENT: "tu comentario",
    },
    Locale.EN: {
        EntityType.REQUEST: "your request",
        EntityType.REQUEST_ITEM: "your item",
        EntityType.RESOURCE: "your part",
        EntityType.COLLECTION_CENTER: "your collection center",
        EntityType.SHIPMENT: "your shipment",
        EntityType.COMMENT: "your comment",
    },
}

# Per-category subject line. Every one carries ``{title}`` so a mailbox does not
# collapse notifications from different entities into one thread.
_SUBJECT: dict[Locale, dict[NotificationCategory, str]] = {
    Locale.ES: {
        NotificationCategory.MENTION: "{actor} te mencionó en «{title}»",
        NotificationCategory.COMMENT: "Nuevo comentario en «{title}»",
        NotificationCategory.STATUS_CHANGE: "Cambio de estado en «{title}»",
        NotificationCategory.ITEM_ADDED: "Nuevo ítem en «{title}»",
        NotificationCategory.TRACKING_UPDATE: "Avance de seguimiento en «{title}»",
        NotificationCategory.REQUEST_REVIEWED: "Tu campaña «{title}» fue revisada",
        NotificationCategory.REVIEW_QUEUE: "Campaña pendiente de revisión: «{title}»",
        NotificationCategory.REACTION: "A {actor} le gustó «{title}»",
    },
    Locale.EN: {
        NotificationCategory.MENTION: "{actor} mentioned you in «{title}»",
        NotificationCategory.COMMENT: "New comment on «{title}»",
        NotificationCategory.STATUS_CHANGE: "Status change on «{title}»",
        NotificationCategory.ITEM_ADDED: "New item on «{title}»",
        NotificationCategory.TRACKING_UPDATE: "Tracking update on «{title}»",
        NotificationCategory.REQUEST_REVIEWED: "Your campaign «{title}» was reviewed",
        NotificationCategory.REVIEW_QUEUE: "Campaign pending review: «{title}»",
        NotificationCategory.REACTION: "{actor} liked «{title}»",
    },
}

# The bold action phrase for the lead line ("{actor} <b>{action}</b> {prep} …").
_ACTION: dict[Locale, dict[NotificationCategory, str]] = {
    Locale.ES: {
        NotificationCategory.MENTION: "te mencionó",
        NotificationCategory.COMMENT: "comentó",
        NotificationCategory.STATUS_CHANGE: "cambió el estado",
        NotificationCategory.ITEM_ADDED: "agregó un ítem",
        NotificationCategory.TRACKING_UPDATE: "publicó un avance",
        NotificationCategory.REQUEST_REVIEWED: "revisó tu campaña",
        NotificationCategory.REVIEW_QUEUE: "envió una campaña para revisión",
        NotificationCategory.REACTION: "le gustó",
    },
    Locale.EN: {
        NotificationCategory.MENTION: "mentioned you",
        NotificationCategory.COMMENT: "commented",
        NotificationCategory.STATUS_CHANGE: "changed the status",
        NotificationCategory.ITEM_ADDED: "added an item",
        NotificationCategory.TRACKING_UPDATE: "posted an update",
        NotificationCategory.REQUEST_REVIEWED: "reviewed your campaign",
        NotificationCategory.REVIEW_QUEUE: "submitted a campaign for review",
        NotificationCategory.REACTION: "liked",
    },
}

# Standalone UI strings by locale.
_STRINGS: dict[Locale, dict[str, str]] = {
    Locale.ES: {
        "greeting": "Hola,",
        "prep": "en",
        "open_here": "Ábrelo aquí:",
        "view": "Ver",
        "open_generic": "Abrir en PrintForHelp",
        "someone": "Alguien",
        "footer_q": (
            "¿Quieres cambiar con qué frecuencia recibes correos de PrintForHelp?"
        ),
        "footer_link": "Haz clic aquí",
    },
    Locale.EN: {
        "greeting": "Hi,",
        "prep": "on",
        "open_here": "Open it here:",
        "view": "View",
        "open_generic": "Open in PrintForHelp",
        "someone": "Someone",
        "footer_q": "Want to change how often you get emails from PrintForHelp?",
        "footer_link": "click here",
    },
}


def render_notification_email(
    db: Session,
    row: models.NotificationEmailOutbox,
    locale: Locale = Locale.ES,
) -> tuple[str, str, str]:
    """Build ``(subject, text_body, html_body)`` in the recipient's locale."""
    loc = locale if locale in _STRINGS else Locale.ES
    s = _STRINGS[loc]
    category = NotificationCategory(row.category)
    actor = _actor_username(db, row.actor_user_id, s["someone"])
    title = row.payload.get("title", "") or "PrintForHelp"
    entity_type = _entity_type(row.entity_type)
    noun = _ENTITY_NOUN[loc].get(entity_type) if entity_type else None
    comment = _comment(db, row.comment_id)
    # A free-text note carried on the notification (e.g. a tracking update's
    # message); shown in a card like a comment when there is no comment.
    note = row.payload.get("note") if comment is None else None

    subject = _SUBJECT[loc][category].format(actor=actor, title=title)
    action = _ACTION[loc][category]
    button = f"{s['view']} {noun}" if noun else s["open_generic"]
    # Reactions read "liked your part" — a possessive noun and no preposition —
    # to match the in-app copy. Every other category reads "<verb> on the part".
    if category is NotificationCategory.REACTION and entity_type is not None:
        lead_noun = _REACTION_NOUN[loc].get(entity_type, noun or "PrintForHelp")
        prep = ""
    else:
        lead_noun = noun or "PrintForHelp"
        prep = s["prep"]
    # Running like total, cached on a reaction notification's payload, so the
    # email can show a "❤ N" badge.
    like_count: int | None = None
    if category is NotificationCategory.REACTION:
        raw = row.payload.get("like_count", "")
        like_count = int(raw) if raw.isdigit() else None

    anchor = row.payload.get("anchor")
    if anchor is None and comment is not None:
        anchor = f"comment-{comment.id}"
    url = _absolute_url(row.payload.get("link", ""), anchor)
    manage_url = f"{settings.PUBLIC_APP_BASE_URL.rstrip('/')}/settings/notifications"

    ctx = _Ctx(
        locale=loc,
        strings=s,
        actor=actor,
        action=action,
        prep=prep,
        lead_noun=lead_noun,
        title=title,
        comment=comment,
        note=note,
        like_count=like_count,
        url=url,
        button=button,
        manage_url=manage_url,
    )
    html = _html_body(ctx) + _hidden_marker(str(row.id))
    return subject, _text_body(ctx), html


class _Ctx:
    """Bundle of resolved, localized values shared by the two renderers."""

    def __init__(
        self,
        *,
        locale: Locale,
        strings: dict[str, str],
        actor: str,
        action: str,
        prep: str,
        lead_noun: str,
        title: str,
        comment: Comment | None,
        note: str | None,
        like_count: int | None,
        url: str,
        button: str,
        manage_url: str,
    ) -> None:
        self.locale = locale
        self.s = strings
        self.actor = actor
        self.action = action
        # Preposition between verb and noun ("on"/"en"); empty for reactions
        # ("liked your part") so the lead has no dangling word.
        self.prep = prep
        self.lead_noun = lead_noun
        self.title = title
        self.comment = comment
        self.note = note
        # Running like total for a reaction email's "❤ N" badge; None otherwise.
        self.like_count = like_count
        self.url = url
        self.button = button
        self.manage_url = manage_url


def _lead_text(ctx: _Ctx) -> str:
    """The lead sentence ("<actor> <verb> [prep] <noun>"), prep optional."""
    parts = [ctx.actor, ctx.action]
    if ctx.prep:
        parts.append(ctx.prep)
    parts.append(ctx.lead_noun)
    return " ".join(parts)


def _likes_label(count: int, locale: Locale) -> str:
    """Localized word after a like count ("likes" / "Me gusta")."""
    if locale is Locale.EN:
        return "like" if count == 1 else "likes"
    return "Me gusta"  # Spanish is invariant ("5 Me gusta")


def _text_body(ctx: _Ctx) -> str:
    """The plain-text fallback part."""
    lines = [
        ctx.s["greeting"],
        "",
        f"{_lead_text(ctx)}: «{ctx.title}»",
    ]
    if ctx.like_count is not None:
        lines += ["", f"♥ {ctx.like_count} {_likes_label(ctx.like_count, ctx.locale)}"]
    if ctx.comment is not None:
        body = _clip(ctx.comment.body)
        meta = f"{ctx.actor} · {_format_dt(ctx.comment.created_at, ctx.locale)}"
        lines += ["", meta, body]
    elif ctx.note is not None:
        lines += ["", f"{ctx.actor}:", _clip(ctx.note)]
    lines += [
        "",
        f"{ctx.s['open_here']}\n{ctx.url}",
        "",
        "—",
        f"{ctx.s['footer_q']} {ctx.s['footer_link']}: {ctx.manage_url}",
    ]
    return "\n".join(lines)


def _html_body(ctx: _Ctx) -> str:
    """The styled HTML part (inlined CSS, hyperlinks, no external assets)."""
    actor = html_lib.escape(ctx.actor)
    action = html_lib.escape(ctx.action)
    prep = html_lib.escape(ctx.prep)
    lead_noun = html_lib.escape(ctx.lead_noun)
    title = html_lib.escape(ctx.title)
    url_attr = html_lib.escape(ctx.url, quote=True)
    manage_attr = html_lib.escape(ctx.manage_url, quote=True)
    button = html_lib.escape(ctx.button)
    footer_q = html_lib.escape(ctx.s["footer_q"])
    footer_link = html_lib.escape(ctx.s["footer_link"])

    # Prep is empty for reactions ("liked your part"); drop the extra space.
    lead_prep = f"{prep} " if prep else ""
    lead = (
        f'<p style="margin:0 0 4px;font-size:15px;line-height:1.5;'
        f'color:{_FOREGROUND};">'
        f"{actor} <strong>{action}</strong> {lead_prep}{lead_noun}:</p>"
    )
    title_block = (
        f'<p style="margin:0 0 16px;font-size:16px;font-weight:600;'
        f'color:{_FOREGROUND};">«{title}»</p>'
    )
    # A "❤ N likes" badge on reaction emails, shown above any comment card so
    # the recipient sees the like total at a glance.
    badge = (
        _reaction_badge_html(ctx.like_count, ctx.locale)
        if ctx.like_count is not None
        else ""
    )
    if ctx.comment is not None:
        card = _comment_card_html(actor, ctx.comment, ctx.locale)
    elif ctx.note is not None:
        card = _note_card_html(actor, ctx.note)
    else:
        card = ""
    # The preferences line lives inside the main content (not a separate
    # bottom bar): a standalone, byte-identical footer block reads to Gmail as
    # a signature and gets collapsed behind a "…". Keeping it in the flow, plus
    # the per-email unique marker appended in ``render_notification_email``,
    # keeps it always visible.
    footer = (
        f'<p style="margin:24px 0 0;padding-top:16px;'
        f"border-top:1px solid {_CARD_BORDER};font-size:12px;line-height:1.5;"
        f'color:{_MUTED};">{footer_q} '
        f'<a href="{manage_attr}" style="color:{_ACCENT_STRONG};'
        f'text-decoration:underline;">{footer_link}</a>.</p>'
    )
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
      {badge}
      {card}
      <a href="{url_attr}" style="display:inline-block;margin-top:20px;\
background:{_ACCENT};color:#ffffff;text-decoration:none;padding:11px 20px;\
border-radius:8px;font-size:14px;font-weight:600;">{button}</a>
      {footer}
    </div>
  </div>
</div>"""


def _hidden_marker(ref: str) -> str:
    """A visually-hidden, per-email unique string.

    Gmail collapses content it fingerprints as a repeated signature (the "…").
    A unique marker at the very end makes every email's trailing bytes differ,
    so the preferences line is not mistaken for a repeated block.
    """
    return (
        '<div style="display:none;max-height:0;max-width:0;overflow:hidden;'
        f'opacity:0;color:transparent;font-size:1px;line-height:1px;">{ref}</div>'
    )


def _reaction_badge_html(count: int, locale: Locale) -> str:
    """A red-heart "❤ N likes" pill for reaction emails (unicode, no image)."""
    label = html_lib.escape(_likes_label(count, locale))
    return (
        '<div style="display:inline-flex;align-items:center;gap:6px;'
        "margin:0 0 4px;padding:8px 14px;border-radius:999px;"
        'background:#fff1f2;border:1px solid #fecdd3;">'
        '<span style="color:#ef4444;font-size:18px;line-height:1;">&#10084;</span>'
        f'<span style="font-size:14px;font-weight:600;color:{_FOREGROUND};">'
        f"{count} {label}</span></div>"
    )


def _comment_card_html(actor: str, comment: Comment, locale: Locale) -> str:
    """A comment card mimicking the on-page one (avatar + meta + body)."""
    meta = f"{actor} · {_format_dt(comment.created_at, locale)}"
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


def _format_dt(dt: datetime, locale: Locale) -> str:
    """Format a timestamp in the recipient's locale (UTC as stored)."""
    month = _MONTHS[locale][dt.month - 1]
    time = f"{dt.hour:02d}:{dt.minute:02d}"
    if locale is Locale.EN:
        return f"{month} {dt.day}, {dt.year}, {time}"
    return f"{dt.day} {month} {dt.year}, {time}"


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


def _actor_username(db: Session, actor_user_id: uuid.UUID, fallback: str) -> str:
    """Return the actor's username, or a neutral fallback if since removed."""
    username = db.query(User.username).filter(User.id == actor_user_id).scalar()
    return username or fallback


def _absolute_url(link: str, anchor: str | None) -> str:
    """Turn a stored relative ``link`` (+ optional anchor) into an absolute URL."""
    base = settings.PUBLIC_APP_BASE_URL.rstrip("/")
    url = f"{base}{link}" if link.startswith("/") else f"{base}/{link}"
    if anchor and "#" not in link:
        url = f"{url}#{anchor}"
    return url
