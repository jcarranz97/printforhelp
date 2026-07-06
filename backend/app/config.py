"""Application configuration via Pydantic settings.

All values can be overridden through environment variables (or a local
``.env`` file). The default admin credentials follow the bootstrap
pattern from FR-007 and are configurable on deploy.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

# Insecure placeholder defaults. Startup refuses to run with these when
# not in DEBUG (see app/bootstrap.py). Kept here so both the field
# defaults and the startup guard reference the same value.
INSECURE_SECRET_KEY = "change-me-in-production"
INSECURE_ADMIN_PASSWORD = "printforhelp-admin"


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "PrintForHelp API"
    VERSION: str = "0.1.0"
    # Off by default: only turns on SQL echo. Enable explicitly in local dev.
    DEBUG: bool = False

    DATABASE_URL: str = (
        "postgresql://printforhelp_user:printforhelp_password"
        "@localhost:5432/printforhelp_db"
    )

    # JWT / auth (NFR-004, NFR-005)
    SECRET_KEY: str = INSECURE_SECRET_KEY
    ALGORITHM: str = "HS256"
    # 7-day sessions for v1 — no refresh-token flow yet.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    # How long a password-reset link stays valid, in minutes.
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate limiting (per client IP) on abuse-prone endpoints. Disabled in
    # the test suite so it does not interfere with functional tests.
    RATE_LIMIT_ENABLED: bool = True

    # "Sign in with Google". Only the Client ID is needed to verify the
    # id_token Google Identity Services hands the browser (the audience
    # check). It is public — it also ships to the frontend — so it can be
    # committed. Empty disables the Google login endpoint.
    GOOGLE_CLIENT_ID: str = ""

    # Outgoing email (SMTP). Used for the "forgot my password" flow. When
    # ``SMTP_HOST`` is empty the app does not try to send anything and just
    # logs the message instead — handy for local dev without a mail server.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    # STARTTLS upgrade on a plain connection (typical on port 587).
    SMTP_USE_TLS: bool = True
    # Implicit TLS from the start (SMTPS, typical on port 465). Set this
    # instead of SMTP_USE_TLS when the provider uses port 465.
    SMTP_USE_SSL: bool = False
    EMAIL_FROM: str = "PrintForHelp <no-reply@printforhelp.org>"

    ALLOWED_HOSTS: list[str] = [
        "http://localhost:3001",
        "http://localhost:3000",
    ]

    # Public base URL of the frontend, used to build the item-tracking URLs
    # that QR codes encode (``{PUBLIC_APP_BASE_URL}/track/{token}``). Set to
    # the deployed domain (e.g. ``https://printforhelp.org``) in production.
    PUBLIC_APP_BASE_URL: str = "http://localhost:3001"

    # Default admin bootstrap (FR-007).
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = INSECURE_ADMIN_PASSWORD

    # Local-development seeding. When true, the app seeds a maintainer
    # and a regular user on startup (in addition to the bootstrap admin).
    SEED_DEV_DATA: bool = False
    SEED_DEV_PASSWORD: str = "printforhelp1"

    # Image uploads / media storage. v1 uses the local-disk backend; an
    # S3-compatible backend (MinIO / R2 / S3) can drop in later behind
    # ``app.storage.Storage`` — its config (bucket / endpoint / region /
    # access keys / public URL) is added alongside that implementation.
    STORAGE_BACKEND: str = "local"
    MEDIA_ROOT: str = "media"
    # Prefix for stored media URLs. Empty (the default) yields *relative*
    # URLs like ``/media/images/x.png`` so they work on any origin — the
    # frontend proxies ``/media`` to the backend (see next.config rewrites),
    # and a production ingress routes it the same way. Set to an absolute
    # base only when media is served from a different host (e.g. an S3
    # bucket / CDN).
    MEDIA_BASE_URL: str = ""
    # Generous enough for a modern phone photo (high-res JPEG/HEIC), which
    # routinely exceeds 5 MB; the image is downscaled and re-encoded on
    # upload anyway, so this is only an inbound safety cap.
    MAX_IMAGE_BYTES: int = 20 * 1024 * 1024
    # Max size for an uploaded model/source file (STL, 3MF, ZIP, ...).
    MAX_UPLOAD_FILE_BYTES: int = 100 * 1024 * 1024


settings = Settings()
