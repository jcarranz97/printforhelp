"""Unguessable public tracking tokens.

Kept in its own dependency-free module because two domains mint them and they
point at each other: ``shipments`` needs a token for every box, while
``tracking`` reads the shipments graph to waterfall box updates down onto the
group and unit timelines. Importing this instead of ``tracking.service`` keeps
that from being an import cycle.
"""

import secrets

from .constants import TRACKING_TOKEN_BYTES


def new_token() -> str:
    """Return a fresh, unguessable token for a public ``/track/{token}`` URL."""
    return secrets.token_urlsafe(TRACKING_TOKEN_BYTES)
