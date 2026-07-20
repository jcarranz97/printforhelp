"""Enums and constants for the notifications domain.

In-app watch subscriptions and notifications. A ``Watch`` row subscribes
a user to a polymorphic entity (the same ``entity_type`` + ``entity_id``
pair used by the activity log); a ``Notification`` is the per-recipient
record fanned out when a watched entity sees activity or when the user is
mentioned in a comment.

Notifications are multi-channel: each is delivered in-app and/or by email
according to the recipient's per-category preference. ``NotificationCategory``
groups the (reason, event) space into the toggles shown in the preference
center; ``CATEGORY_DEFAULTS`` holds the opt-out defaults applied until a user
customizes them. (Email delivery goes through the ``NotificationEmailOutbox``
transactional outbox, not the older per-row ``emailed_at`` digest hook, which
stays unused.)
"""

from enum import StrEnum

from app.activity.constants import ActivityAction


class NotificationReason(StrEnum):
    """Why a recipient received a notification."""

    MENTION = "mention"  # named with @username in a comment
    WATCH = "watch"  # subscribed to the entity
    MODERATION = "moderation"  # a review queue event (not a subscription)


class NotificationCategory(StrEnum):
    """User-facing grouping of notifications, keyed by (reason, event).

    Each category is one row in the preference center with an in-app and an
    email toggle. The keys are stable and stored in
    ``notification_preferences.category`` / ``notification_email_outbox``.
    """

    MENTION = "mention"  # someone @mentioned you
    COMMENT = "comment"  # new comment on something you follow
    STATUS_CHANGE = "status_change"  # status moved on something you follow
    ITEM_ADDED = "item_added"  # a line item was added to a campaign you follow
    TRACKING_UPDATE = "tracking_update"  # QR/print progress on something you follow
    REQUEST_REVIEWED = "request_reviewed"  # your campaign was approved / rejected
    REVIEW_QUEUE = "review_queue"  # a campaign needs review (maintainers/admins)
    REACTION = "reaction"  # someone liked your post or comment


# Per-category delivery defaults as ``(in_app_enabled, email_enabled)`` when
# the user has no stored preference row. In-app is on for everything; email is
# on by default except for the high-volume/low-urgency ``status_change`` and
# ``item_added`` categories.
CATEGORY_DEFAULTS: dict[NotificationCategory, tuple[bool, bool]] = {
    NotificationCategory.MENTION: (True, True),
    NotificationCategory.COMMENT: (True, True),
    NotificationCategory.STATUS_CHANGE: (True, False),
    NotificationCategory.ITEM_ADDED: (True, False),
    NotificationCategory.TRACKING_UPDATE: (True, True),
    NotificationCategory.REQUEST_REVIEWED: (True, True),
    NotificationCategory.REVIEW_QUEUE: (True, True),
    # Likes are high-volume / low-urgency, so email is off by default; users
    # who want a mail per like can opt in from the preference center.
    NotificationCategory.REACTION: (True, False),
}

# Categories only surfaced to maintainers/admins in the preference center
# (the review queue is a role capability, not something regular users see).
MAINTAINER_ONLY_CATEGORIES: frozenset[NotificationCategory] = frozenset(
    {NotificationCategory.REVIEW_QUEUE}
)


# Activity actions that fan a notification out to an entity's watchers.
# Intentionally small; extend as more lifecycle events warrant a ping.
NOTIFY_ACTIONS: frozenset[ActivityAction] = frozenset(
    {
        ActivityAction.COMMENTED,
        ActivityAction.STATUS_CHANGED,
        ActivityAction.ITEM_ADDED,
    }
)

# Activity actions that auto-subscribe the actor to the entity (JIRA-style:
# you watch what you create, comment on, or move through a status change).
AUTO_WATCH_ACTIONS: frozenset[ActivityAction] = frozenset(
    {
        ActivityAction.CREATED,
        ActivityAction.COMMENTED,
        ActivityAction.STATUS_CHANGED,
    }
)

# ``event`` value stored for an @mention notification (distinct from any
# ActivityAction so the UI can render mention-specific copy).
MENTION_EVENT = "mentioned"

# ``event`` value stored when a new record is posted on a watched QR
# tracking timeline (group or one of its items). Distinct from any
# ActivityAction so the UI can render tracking-specific copy.
TRACKING_UPDATE_EVENT = "tracking_update"

# ``event`` values for the Request moderation queue. ``REQUEST_SUBMITTED``
# pings maintainers/admins that a campaign needs review; ``REQUEST_REVIEWED``
# tells the author the verdict (approved / more info needed / rejected).
REQUEST_SUBMITTED_EVENT = "request_submitted"
REQUEST_REVIEWED_EVENT = "request_reviewed"

# ``event`` value stored when someone reacts ("likes") a post or comment.
# Distinct from any ActivityAction so the UI/email can render like-specific
# copy.
REACTION_EVENT = "reaction"

# Maps a notification's (reason, event) onto the user-facing category whose
# in-app / email toggles gate it. ``event`` values that are ActivityAction
# names (``commented`` / ``status_changed`` / ``item_added``) are matched by
# their string value to avoid importing the whole enum here.
_EVENT_TO_CATEGORY: dict[str, NotificationCategory] = {
    ActivityAction.COMMENTED.value: NotificationCategory.COMMENT,
    ActivityAction.STATUS_CHANGED.value: NotificationCategory.STATUS_CHANGE,
    ActivityAction.ITEM_ADDED.value: NotificationCategory.ITEM_ADDED,
    TRACKING_UPDATE_EVENT: NotificationCategory.TRACKING_UPDATE,
    REQUEST_SUBMITTED_EVENT: NotificationCategory.REVIEW_QUEUE,
    REQUEST_REVIEWED_EVENT: NotificationCategory.REQUEST_REVIEWED,
    REACTION_EVENT: NotificationCategory.REACTION,
    MENTION_EVENT: NotificationCategory.MENTION,
}


def category_for(reason: NotificationReason, event: str) -> NotificationCategory:
    """Return the preference category a (reason, event) notification belongs to.

    A mention is always the ``MENTION`` category regardless of event; otherwise
    the event string selects the category. Falls back to ``COMMENT`` for any
    unmapped event so a new event still delivers (in-app + email on by default)
    rather than silently vanishing.
    """
    if reason is NotificationReason.MENTION:
        return NotificationCategory.MENTION
    return _EVENT_TO_CATEGORY.get(event, NotificationCategory.COMMENT)


# Matches @username tokens in a comment body. The leading lookbehind keeps
# email addresses (``user@host``) from matching — a bare ``contacto@fablab.org``
# in prose has a word character before the ``@`` — and the capture must start
# with an alphanumeric so trailing punctuation is excluded.
#
# The optional ``@domain`` tail exists for **legacy handles**: usernames are
# URL-safe today, but rows created before that validation can be full email
# addresses, and those users must still be taggable. The tail is matched
# greedily and the resolver falls back to the part before it, so
# ``@someone@gmail.com`` still tags ``someone`` when that is who exists.
# ``+`` is allowed in the local part for the same legacy reason.
MENTION_PATTERN = (
    r"(?<![\w@])@([A-Za-z0-9][A-Za-z0-9_.+-]{0,63}"
    r"(?:@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,62}[A-Za-z0-9])?)?)"
)

# Cap mentions resolved per comment to bound work and discourage abuse.
MAX_MENTIONS_PER_COMMENT = 20

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class ErrorCode(StrEnum):
    """Error codes raised by the notifications domain."""

    INVALID_WATCH_TARGET = "INVALID_WATCH_TARGET"
    INVALID_MARK_READ_REQUEST = "INVALID_MARK_READ_REQUEST"
    UNKNOWN_NOTIFICATION_CATEGORY = "UNKNOWN_NOTIFICATION_CATEGORY"
    INVALID_UNSUBSCRIBE_TOKEN = "INVALID_UNSUBSCRIBE_TOKEN"
