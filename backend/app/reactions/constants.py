"""Enums and constants for the reactions domain.

A reaction is a lightweight, polymorphic "like": a ``(user, entity_type,
entity_id, reaction_type)`` row that mirrors the watch / comment plumbing.
v1 ships a single Instagram-style heart (``reaction_type == "like"``); the
column is stored on every row so a future multi-emoji feature needs no
migration. The frontend only surfaces an aggregate count and whether the
viewer reacted — who reacted is kept in the table for a later "see who
liked" feature but never returned in v1.
"""

from enum import StrEnum

# The single reaction kind in v1. Stored explicitly so richer reactions can
# be added later without a schema change.
DEFAULT_REACTION_TYPE = "like"

# Upper bound on the entity ids a single batch state read may request, so the
# comment-feed lookup can fetch every visible comment's count in one call
# without turning into an unbounded query.
MAX_BATCH_ENTITY_IDS = 200


class ErrorCode(StrEnum):
    """Error codes raised by the reactions domain."""

    INVALID_REACTION_TARGET = "INVALID_REACTION_TARGET"
