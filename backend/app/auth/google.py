"""Verify Google Identity Services id_tokens.

The frontend uses Google Identity Services, which hands the browser a
signed ``id_token`` (a JWT). We verify its signature against Google's
public keys and check the audience (our Client ID) and issuer. No client
secret is needed for this flow — only the public Client ID.
"""

import logging

import jwt
from jwt import PyJWKClient

from app.config import settings

from .exceptions import InvalidGoogleTokenExceptionError

logger = logging.getLogger(__name__)

_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ALLOWED_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
# Tolerate small clock differences between us and Google so a token whose
# ``iat``/``exp`` is a few seconds off is not wrongly rejected.
_CLOCK_SKEW_LEEWAY_SECONDS = 30

_jwks_client = PyJWKClient(_GOOGLE_CERTS_URL)


def verify_google_id_token(id_token: str) -> dict[str, object]:
    """Return the verified claims of a Google id_token, or raise.

    Checks the RS256 signature (against Google's published keys), that the
    audience matches our Client ID, and that the issuer is Google. Raises
    ``InvalidGoogleTokenExceptionError`` on any problem.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise InvalidGoogleTokenExceptionError

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(id_token)
        claims: dict[str, object] = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            leeway=_CLOCK_SKEW_LEEWAY_SECONDS,
        )
    except jwt.PyJWTError as exc:
        logger.warning("Google id_token rejected: %s: %s", type(exc).__name__, exc)
        raise InvalidGoogleTokenExceptionError from exc

    if claims.get("iss") not in _ALLOWED_ISSUERS:
        logger.warning("Google id_token bad issuer: %s", claims.get("iss"))
        raise InvalidGoogleTokenExceptionError
    return claims
