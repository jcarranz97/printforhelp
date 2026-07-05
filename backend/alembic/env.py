"""Alembic migration environment."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import settings and metadata. Importing the model modules registers
# every table on Base.metadata so autogenerate can see them.
from app.config import settings
from app.models import Base

import app.activity.models  # noqa: F401  (registers activity_log + comments)
import app.audit_log.models  # noqa: F401  (registers audit_log table)
import app.auth.models  # noqa: F401  (registers password_reset_tokens table)
import app.collection_centers.models  # noqa: F401  (registers cc tables)
import app.contributions.models  # noqa: F401  (registers contributions table)
import app.notifications.models  # noqa: F401  (registers watches + notifications)
import app.organizations.models  # noqa: F401  (registers org tables)
import app.resources.models  # noqa: F401  (registers resources table)
import app.requests.models  # noqa: F401  (registers requests + items tables)
import app.shipments.models  # noqa: F401  (registers shipments table)
import app.tracking.models  # noqa: F401  (registers tracking tables)
import app.users.models  # noqa: F401  (registers users table)

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DB connection)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
