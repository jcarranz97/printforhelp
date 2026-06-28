"""Application configuration via Pydantic settings.

All values can be overridden through environment variables (or a local
``.env`` file). The default admin credentials follow the bootstrap
pattern from FR-007 and are configurable on deploy.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "PrintForHelp API"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = (
        "postgresql://printforhelp_user:printforhelp_password"
        "@localhost:5432/printforhelp_db"
    )

    # JWT / auth (NFR-004, NFR-005)
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    # 7-day sessions for v1 — no refresh-token flow yet.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    ALLOWED_HOSTS: list[str] = [
        "http://localhost:3001",
        "http://localhost:3000",
    ]

    # Default admin bootstrap (FR-007).
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "printforhelp-admin"

    # Local-development seeding. When true, the app seeds a maintainer
    # and a regular user on startup (in addition to the bootstrap admin).
    SEED_DEV_DATA: bool = False
    SEED_DEV_PASSWORD: str = "printforhelp1"


settings = Settings()
