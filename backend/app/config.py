from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_NAME: str = "PrintForHelp API"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://printforhelp_user:printforhelp_password@localhost:5432/printforhelp_db"

    SECRET_KEY: str = "change-me-in-production"

    ALLOWED_HOSTS: list = [
        "http://localhost:3001",
        "http://localhost:3000",
    ]

    class Config:
        """Configuration for environment file."""

        env_file = ".env"


settings = Settings()
