"""Rate limiting for abuse-prone endpoints (login, password reset, ...).

Uses slowapi keyed by the client IP. Behind a reverse proxy, make the
proxy pass the real client IP — ``get_remote_address`` reads
``request.client.host``. Limiting is toggled by ``RATE_LIMIT_ENABLED``
(off during tests so functional tests are not throttled).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)

# Per-IP limits. Login/reset are the brute-force targets; forgot-password
# is the email-spam target (each call can send an email).
LOGIN_LIMIT = "10/minute"
REGISTER_LIMIT = "5/minute"
GOOGLE_LOGIN_LIMIT = "10/minute"
FORGOT_PASSWORD_LIMIT = "5/minute"
RESET_PASSWORD_LIMIT = "10/minute"
