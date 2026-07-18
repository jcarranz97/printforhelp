"""Watch-subscription and in-app notification business logic.

Notifications are fanned out from a single choke point: the activity
``record`` function calls :func:`fan_out_to_watchers` (for lifecycle and
comment events) and :func:`ensure_watch` (to auto-subscribe the actor),
while :func:`create_mention_notifications` handles ``@username`` mentions
parsed from comment bodies. The write helpers used inside that flow flush
only -- the mutation that triggered them owns the commit -- so a
notification is atomic with the event that produced it. The router-facing
watch / mark-read helpers own their own transaction.

Each fan-out gates delivery per recipient in :func:`_deliver`: it writes an
in-app ``Notification`` and/or a ``NotificationEmailOutbox`` row according to
the recipient's per-category preference. The outbox is drained by a
background worker (``app.scheduled``) that sends the email over SMTP.
"""

import logging
import re
import smtplib
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.activity import validators
from app.activity.constants import EntityType
from app.activity.models import Comment
from app.collection_centers.models import CollectionCenter
from app.config import settings
from app.contributions.models import Contribution
from app.requests.models import Request, RequestItem
from app.resources.models import Resource
from app.shipments.models import Shipment
from app.tracking.models import TrackingGroup
from app.users.constants import UserRole
from app.users.models import User
from app.users.service import get_user_by_username

from . import models
from .constants import (
    CATEGORY_DEFAULTS,
    DEFAULT_PAGE_SIZE,
    MAX_MENTIONS_PER_COMMENT,
    MAX_PAGE_SIZE,
    MENTION_EVENT,
    MENTION_PATTERN,
    NotificationCategory,
    NotificationReason,
    category_for,
)
from .exceptions import (
    InvalidMarkReadRequestExceptionError,
    InvalidWatchTargetExceptionError,
)

_MENTION_RE = re.compile(MENTION_PATTERN)


# --------------------------------------------------------------------------
# Watch subscriptions
# --------------------------------------------------------------------------


def _active_watch(
    db: Session,
    user_id: uuid.UUID,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> models.Watch | None:
    """Return the active Watch row for (user, entity), or None."""
    return (
        db.query(models.Watch)
        .filter(
            models.Watch.user_id == user_id,
            models.Watch.entity_type == entity_type.value,
            models.Watch.entity_id == entity_id,
            models.Watch.active.is_(True),
        )
        .first()
    )


def ensure_watch(
    db: Session,
    user_id: uuid.UUID,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> None:
    """Idempotently subscribe a user to an entity (flush only).

    Reactivates a previously unwatched row instead of inserting a duplicate,
    keeping at most one row per (user, entity).
    """
    existing = (
        db.query(models.Watch)
        .filter(
            models.Watch.user_id == user_id,
            models.Watch.entity_type == entity_type.value,
            models.Watch.entity_id == entity_id,
        )
        .first()
    )
    if existing is not None:
        if not existing.active:
            existing.active = True
            db.flush()
        return
    db.add(
        models.Watch(
            user_id=user_id,
            entity_type=entity_type.value,
            entity_id=entity_id,
        )
    )
    db.flush()


def watch_entity(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> None:
    """Manually subscribe via the API; validates the target exists and is visible.

    The visibility check matters for a Request's private review thread (and for
    an unpublished campaign): without it a stranger could subscribe and learn
    from the notifications alone that a conversation is happening, even though
    they can never read it.
    """
    if not validators.entity_exists(db, entity_type, entity_id):
        raise InvalidWatchTargetExceptionError(entity_type.value, entity_id)
    if not validators.is_entity_visible(db, entity_type, entity_id, user):
        raise InvalidWatchTargetExceptionError(entity_type.value, entity_id)
    ensure_watch(db, user.id, entity_type, entity_id)
    db.commit()


def unwatch_entity(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> None:
    """Soft-delete the user's subscription to an entity (no-op if absent)."""
    watch = _active_watch(db, user.id, entity_type, entity_id)
    if watch is not None:
        watch.active = False
        db.commit()


def is_watching(
    db: Session,
    *,
    user: User,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> bool:
    """Return True if the user has an active subscription to the entity."""
    return _active_watch(db, user.id, entity_type, entity_id) is not None


# --------------------------------------------------------------------------
# Notification fan-out
# --------------------------------------------------------------------------


def _channel_prefs(
    db: Session,
    recipient_ids: set[uuid.UUID],
    category: NotificationCategory,
) -> dict[uuid.UUID, tuple[bool, bool]]:
    """Resolve each recipient's ``(in_app, email)`` choice for a category.

    One query for the whole recipient set; users with no stored row fall back
    to ``CATEGORY_DEFAULTS`` so the opt-out defaults apply until they visit
    the preference center.
    """
    default = CATEGORY_DEFAULTS[category]
    prefs: dict[uuid.UUID, tuple[bool, bool]] = dict.fromkeys(recipient_ids, default)
    rows = (
        db.query(
            models.NotificationPreference.user_id,
            models.NotificationPreference.in_app_enabled,
            models.NotificationPreference.email_enabled,
        )
        .filter(
            models.NotificationPreference.user_id.in_(recipient_ids),
            models.NotificationPreference.category == category.value,
            models.NotificationPreference.active.is_(True),
        )
        .all()
    )
    for user_id, in_app, email in rows:
        prefs[user_id] = (in_app, email)
    return prefs


def _deliver(
    db: Session,
    *,
    recipient_ids: set[uuid.UUID],
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: NotificationReason,
    event: str,
    payload: dict[str, str],
    comment_id: uuid.UUID | None = None,
) -> None:
    """Fan a resolved, active recipient set out across their chosen channels.

    For each recipient the category's ``(in_app, email)`` preference decides
    delivery: an in-app ``Notification`` is written iff in-app is on, and a
    ``NotificationEmailOutbox`` row iff email is on (and emails are enabled
    globally). Both writes are flush-only, so they commit atomically with the
    event that triggered them. Each row gets its own ``payload`` copy so the
    JSONB column is never aliased across recipients.
    """
    if not recipient_ids:
        return
    category = category_for(reason, event)
    prefs = _channel_prefs(db, recipient_ids, category)
    emails_enabled = settings.NOTIFICATION_EMAILS_ENABLED
    for recipient_id in recipient_ids:
        in_app, email = prefs[recipient_id]
        if in_app:
            db.add(
                models.Notification(
                    recipient_user_id=recipient_id,
                    actor_user_id=actor_user_id,
                    entity_type=entity_type.value,
                    entity_id=entity_id,
                    reason=reason.value,
                    event=event,
                    comment_id=comment_id,
                    payload=dict(payload),
                )
            )
        if email and emails_enabled:
            db.add(
                models.NotificationEmailOutbox(
                    recipient_user_id=recipient_id,
                    actor_user_id=actor_user_id,
                    entity_type=entity_type.value,
                    entity_id=entity_id,
                    category=category.value,
                    event=event,
                    comment_id=comment_id,
                    payload=dict(payload),
                )
            )
    db.flush()


def _active_subset(db: Session, user_ids: set[uuid.UUID]) -> set[uuid.UUID]:
    """Return the subset of ``user_ids`` whose accounts are still active."""
    if not user_ids:
        return set()
    return {
        row[0]
        for row in db.query(User.id)
        .filter(User.id.in_(user_ids), User.active.is_(True))
        .all()
    }


def fan_out_to_watchers(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    event: str,
    comment_id: uuid.UUID | None = None,
    exclude_user_ids: set[uuid.UUID] | None = None,
    anchor: str | None = None,
    extra_payload: dict[str, str] | None = None,
) -> None:
    """Notify an entity's active watchers across their chosen channels.

    The actor and any ``exclude_user_ids`` (e.g. users already notified by
    an @mention for the same comment) are skipped, as are inactive accounts.
    ``anchor`` is an optional URL fragment (e.g. ``record-<id>``) cached on
    the notification so a click deep-links to and highlights the exact item
    on the target page (the same treatment @mention/comment notifications get
    from ``comment_id``). ``extra_payload`` merges extra cached fields into the
    notification payload (e.g. a tracking update's ``note`` so the email can
    show it). Per-recipient channel gating happens in :func:`_deliver`.
    """
    excluded = {actor_user_id}
    if exclude_user_ids:
        excluded |= exclude_user_ids
    watcher_ids = {
        row[0]
        for row in db.query(models.Watch.user_id)
        .filter(
            models.Watch.entity_type == entity_type.value,
            models.Watch.entity_id == entity_id,
            models.Watch.active.is_(True),
        )
        .all()
    }
    recipients = _active_subset(db, watcher_ids - excluded)
    if not recipients:
        return
    title, link = _resolve_link_and_title(db, entity_type, entity_id)
    payload: dict[str, str] = {"title": title, "link": link}
    if anchor is not None:
        payload["anchor"] = anchor
    if extra_payload:
        payload.update(extra_payload)
    _deliver(
        db,
        recipient_ids=recipients,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        reason=NotificationReason.WATCH,
        event=event,
        payload=payload,
        comment_id=comment_id,
    )


def fan_out_to_users(
    db: Session,
    *,
    recipient_ids: set[uuid.UUID],
    entity_type: EntityType,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    event: str,
    reason: NotificationReason = NotificationReason.MODERATION,
) -> None:
    """Notify an explicit set of users, bypassing the watch list.

    Used by flows where the recipients are determined by role or ownership
    rather than by subscription — the moderation queue, where maintainers must
    hear about a submission they never opted into, and the author must hear the
    verdict. The actor is skipped (no self-notifications), as are inactive
    accounts. Per-recipient channel gating happens in :func:`_deliver`.
    """
    recipients = _active_subset(db, recipient_ids - {actor_user_id})
    if not recipients:
        return
    title, link = _resolve_link_and_title(db, entity_type, entity_id)
    _deliver(
        db,
        recipient_ids=recipients,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        reason=reason,
        event=event,
        payload={"title": title, "link": link},
    )


def maintainer_user_ids(db: Session) -> set[uuid.UUID]:
    """Return the ids of every active maintainer/admin (the review audience)."""
    return {
        row[0]
        for row in db.query(User.id)
        .filter(
            User.role.in_([UserRole.MAINTAINER, UserRole.ADMIN]),
            User.active.is_(True),
        )
        .all()
    }


def create_mention_notifications(
    db: Session,
    *,
    comment: Comment,
    actor: User,
    previous_body: str | None = None,
) -> set[uuid.UUID]:
    """Notify users named with @username in a comment body (flush only).

    Returns the set of notified recipient ids so the caller can exclude them
    from the watcher fan-out and avoid double-notifying. On an edit,
    ``previous_body`` suppresses users who were already mentioned before the
    edit, so only newly added mentions are pinged.
    """
    usernames = _extract_mentions(comment.body)
    if previous_body is not None:
        already = {name.lower() for name in _extract_mentions(previous_body)}
        usernames = [name for name in usernames if name.lower() not in already]
    if not usernames:
        return set()
    entity_type = EntityType(comment.entity_type)
    title, link = _resolve_link_and_title(db, entity_type, comment.entity_id)
    notified: set[uuid.UUID] = set()
    for username in usernames:
        user = get_user_by_username(db, username)
        if user is None or not user.active:
            continue
        if user.id == actor.id or user.id in notified:
            continue
        notified.add(user.id)
    # The returned set (all resolved mentionees) is what the caller excludes
    # from the watcher fan-out, so a user who turned mention notifications off
    # is still not double-pinged as a watcher of the same comment.
    _deliver(
        db,
        recipient_ids=notified,
        entity_type=entity_type,
        entity_id=comment.entity_id,
        actor_user_id=actor.id,
        reason=NotificationReason.MENTION,
        event=MENTION_EVENT,
        payload={"title": title, "link": link},
        comment_id=comment.id,
    )
    return notified


def _extract_mentions(body: str) -> list[str]:
    """Return up to ``MAX_MENTIONS_PER_COMMENT`` unique @usernames, in order."""
    seen: list[str] = []
    for match in _MENTION_RE.finditer(body):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
        if len(seen) >= MAX_MENTIONS_PER_COMMENT:
            break
    return seen


def entity_title(db: Session, entity_type: EntityType, entity_id: uuid.UUID) -> str:
    """Return an entity's display title (used by unsubscribe-link previews)."""
    title, _ = _resolve_link_and_title(db, entity_type, entity_id)
    return title


def _resolve_link_and_title(
    db: Session,
    entity_type: EntityType,
    entity_id: uuid.UUID,
) -> tuple[str, str]:
    """Build a display title + frontend link for a notification target.

    Resolved once at creation; falls back to a generic title if the entity
    was since removed. The shipment link is nested under its parent center.
    """
    if entity_type is EntityType.COLLECTION_CENTER:
        center = (
            db.query(CollectionCenter).filter(CollectionCenter.id == entity_id).first()
        )
        title = center.name if center is not None else "Collection center"
        return title, f"/centers/{entity_id}"
    if entity_type is EntityType.RESOURCE:
        resource = db.query(Resource).filter(Resource.id == entity_id).first()
        title = resource.name if resource is not None else "Resource"
        return title, f"/parts/{entity_id}"
    if entity_type in (EntityType.REQUEST, EntityType.REQUEST_REVIEW):
        request = db.query(Request).filter(Request.id == entity_id).first()
        title = request.title if request is not None else "Request"
        # Both live on the campaign page; the review thread is an anchor on it.
        anchor = "#review" if entity_type is EntityType.REQUEST_REVIEW else ""
        return title, f"/requests/{entity_id}{anchor}"
    if entity_type is EntityType.REQUEST_ITEM:
        return _request_item_link_and_title(db, entity_id)
    if entity_type is EntityType.TRACKING_GROUP:
        return _tracking_link_and_title(db, entity_id)
    return _shipment_link_and_title(db, entity_id)


def _shipment_link_and_title(db: Session, entity_id: uuid.UUID) -> tuple[str, str]:
    """Build a title + center-nested link for a shipment notification target."""
    shipment = db.query(Shipment).filter(Shipment.id == entity_id).first()
    if shipment is None:
        return "Shipment", "/centers"
    title = shipment.destination or "Shipment"
    return title, f"/centers/{shipment.collection_center_id}/shipments/{entity_id}"


def _request_item_link_and_title(db: Session, item_id: uuid.UUID) -> tuple[str, str]:
    """Build a title (Resource name) + link for a request-item timeline.

    The link points at the **parent Request page** (``/requests/{request_id}``),
    not the item sub-page: an item's comments and activity now surface in that
    item's expandable card on the Request page, and the notification's
    ``#comment-<id>`` / ``#record-<id>`` anchor scrolls to the exact entry there.
    """
    row = (
        db.query(Resource.name, RequestItem.request_id)
        .select_from(RequestItem)
        .join(Resource, Resource.id == RequestItem.resource_id)
        .filter(RequestItem.id == item_id)
        .first()
    )
    if row is None:  # pragma: no cover - item is soft-deleted, never removed
        return "Request item", "/requests"
    name, request_id = row
    return name or "Request item", f"/requests/{request_id}"


def _tracking_link_and_title(db: Session, group_id: uuid.UUID) -> tuple[str, str]:
    """Build a title + public ``/track`` link for a tracking group.

    The title reuses the tracked Contribution's Resource name so a tracking
    notification reads like the entity it belongs to; the link points at the
    public QR timeline via the group's share token. Imported locally to keep
    the tracking timeline's Resource name.
    """
    group = db.query(TrackingGroup).filter(TrackingGroup.id == group_id).first()
    if group is None:  # pragma: no cover - group is soft-deleted, never removed
        return "Tracking", "/track"
    name = (
        db.query(Resource.name)
        .select_from(TrackingGroup)
        .join(Contribution, Contribution.id == TrackingGroup.contribution_id)
        .join(RequestItem, RequestItem.id == Contribution.request_item_id)
        .join(Resource, Resource.id == RequestItem.resource_id)
        .filter(TrackingGroup.id == group_id)
        .scalar()
    )
    return (name or "Tracking"), f"/track/{group.tracking_token}"


# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------


def visible_categories(user: User) -> list[NotificationCategory]:
    """Return the categories a user may configure, in display order.

    The review-queue category is only meaningful to maintainers/admins, so it
    is hidden from everyone else.
    """
    from app.permissions import has_global_override

    from .constants import MAINTAINER_ONLY_CATEGORIES

    is_maintainer = has_global_override(user)
    return [
        category
        for category in NotificationCategory
        if is_maintainer or category not in MAINTAINER_ONLY_CATEGORIES
    ]


def list_preferences(
    db: Session, *, user: User
) -> list[tuple[NotificationCategory, bool, bool]]:
    """Return ``(category, in_app, email)`` for every category the user sees.

    Stored rows win; categories with no row report their default so the UI
    always renders the full matrix.
    """
    stored = {
        NotificationCategory(row.category): (row.in_app_enabled, row.email_enabled)
        for row in db.query(models.NotificationPreference)
        .filter(
            models.NotificationPreference.user_id == user.id,
            models.NotificationPreference.active.is_(True),
        )
        .all()
    }
    result: list[tuple[NotificationCategory, bool, bool]] = []
    for category in visible_categories(user):
        in_app, email = stored.get(category, CATEGORY_DEFAULTS[category])
        result.append((category, in_app, email))
    return result


def set_preference(
    db: Session,
    *,
    user: User,
    category: NotificationCategory,
    in_app_enabled: bool,
    email_enabled: bool,
) -> None:
    """Upsert a user's channel choice for one category (owns its commit)."""
    row = (
        db.query(models.NotificationPreference)
        .filter(
            models.NotificationPreference.user_id == user.id,
            models.NotificationPreference.category == category.value,
            models.NotificationPreference.active.is_(True),
        )
        .first()
    )
    if row is None:
        db.add(
            models.NotificationPreference(
                user_id=user.id,
                category=category.value,
                in_app_enabled=in_app_enabled,
                email_enabled=email_enabled,
            )
        )
    else:
        row.in_app_enabled = in_app_enabled
        row.email_enabled = email_enabled
    db.commit()


# --------------------------------------------------------------------------
# Reads + mark-read
# --------------------------------------------------------------------------


def list_for_user(
    db: Session,
    *,
    user: User,
    limit: int = DEFAULT_PAGE_SIZE,
    before: datetime | None = None,
    unread_only: bool = False,
) -> list[models.Notification]:
    """Return the user's notifications, newest first."""
    limit = min(limit, MAX_PAGE_SIZE)
    query = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == user.id,
        models.Notification.active.is_(True),
    )
    if unread_only:
        query = query.filter(models.Notification.read_at.is_(None))
    if before is not None:
        query = query.filter(models.Notification.created_at < before)
    return query.order_by(desc(models.Notification.created_at)).limit(limit).all()


def unread_count(db: Session, *, user: User) -> int:
    """Count the user's unread notifications (powers the badge)."""
    return (
        db.query(func.count(models.Notification.id))
        .filter(
            models.Notification.recipient_user_id == user.id,
            models.Notification.active.is_(True),
            models.Notification.read_at.is_(None),
        )
        .scalar()
    ) or 0


def mark_read(
    db: Session,
    *,
    user: User,
    ids: list[uuid.UUID] | None = None,
    mark_all: bool = False,
) -> int:
    """Mark the given notifications (or all unread) as read; returns count."""
    if not mark_all and not ids:
        raise InvalidMarkReadRequestExceptionError
    query = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == user.id,
        models.Notification.active.is_(True),
        models.Notification.read_at.is_(None),
    )
    if not mark_all:
        query = query.filter(models.Notification.id.in_(ids or []))
    updated = query.update(
        {models.Notification.read_at: datetime.now(UTC)},
        synchronize_session=False,
    )
    db.commit()
    return updated


# --------------------------------------------------------------------------
# Email delivery (outbox drain)
# --------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def send_pending_notification_emails(
    db: Session,
    *,
    batch_size: int | None = None,
    max_attempts: int | None = None,
) -> int:
    """Send one batch of queued notification emails; return how many shipped.

    Claims its batch with ``FOR UPDATE SKIP LOCKED`` so any number of workers
    (or API replicas) can drain the outbox in parallel without ever sending a
    row twice — each worker grabs a disjoint set and skips rows another worker
    already holds. A row whose recipient is gone/has no email is retired
    (stamped ``sent_at``) rather than retried forever; an SMTP failure bumps
    ``attempts`` and records ``last_error`` until ``max_attempts`` is reached.
    """
    from app.auth.email import send_email

    from .email import render_notification_email

    batch_size = batch_size or settings.NOTIFICATION_EMAIL_BATCH_SIZE
    max_attempts = max_attempts or settings.NOTIFICATION_EMAIL_MAX_ATTEMPTS
    rows = (
        db.query(models.NotificationEmailOutbox)
        .filter(
            models.NotificationEmailOutbox.sent_at.is_(None),
            models.NotificationEmailOutbox.active.is_(True),
            models.NotificationEmailOutbox.attempts < max_attempts,
        )
        .order_by(models.NotificationEmailOutbox.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
        .all()
    )
    sent = 0
    now = datetime.now(UTC)
    for row in rows:
        recipient = db.query(User).filter(User.id == row.recipient_user_id).first()
        if recipient is None or not recipient.active or not recipient.email:
            row.sent_at = now
            row.last_error = "recipient inactive or has no email"
            continue
        try:
            subject, body, html = render_notification_email(
                db, row, recipient.preferred_locale
            )
            send_email(recipient.email, subject, body, html=html)
        except (OSError, smtplib.SMTPException) as exc:
            row.attempts += 1
            row.last_error = str(exc)
            logger.warning(
                "Failed to send notification email %s (attempt %d): %s",
                row.id,
                row.attempts,
                exc,
            )
            continue
        row.sent_at = now
        row.last_error = None
        sent += 1
    db.commit()
    return sent
