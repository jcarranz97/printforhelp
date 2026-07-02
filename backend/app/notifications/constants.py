"""Enums and constants for the notifications domain.

In-app watch subscriptions and notifications. A ``Watch`` row subscribes
a user to a polymorphic entity (the same ``entity_type`` + ``entity_id``
pair used by the activity log); a ``Notification`` is the per-recipient
record fanned out when a watched entity sees activity or when the user is
mentioned in a comment.

v1 is **in-app only**. The unused ``emailed_at`` column on the
notification and the ``reason`` / ``event`` split are forward hooks so a
future opt-in email digest can key off them without a schema rewrite.
"""

from enum import StrEnum

from app.activity.constants import ActivityAction


class NotificationReason(StrEnum):
    """Why a recipient received a notification."""

    MENTION = "mention"  # named with @username in a comment
    WATCH = "watch"  # subscribed to the entity


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

# Matches @username tokens in a comment body. The leading lookbehind keeps
# email addresses (``user@host``) from matching, and the capture must start
# with an alphanumeric so trailing punctuation is excluded.
MENTION_PATTERN = r"(?<![\w@])@([A-Za-z0-9][A-Za-z0-9_.-]{0,63})"

# Cap mentions resolved per comment to bound work and discourage abuse.
MAX_MENTIONS_PER_COMMENT = 20

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class ErrorCode(StrEnum):
    """Error codes raised by the notifications domain."""

    INVALID_WATCH_TARGET = "INVALID_WATCH_TARGET"
    INVALID_MARK_READ_REQUEST = "INVALID_MARK_READ_REQUEST"
