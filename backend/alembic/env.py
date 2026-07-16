"""Alembic migration environment.

The database URL and target metadata come from the application itself, so
migrations always match the app's configuration. ``render_as_batch`` is enabled
for SQLite so that ``ALTER TABLE`` operations (which SQLite barely supports) are
emulated via the table-recreate strategy.
"""

from __future__ import annotations

from logging.config import fileConfig

# Import the model registry so every table is attached to Base.metadata before
# autogenerate inspects it. (Models are added from Step 2 onward.)
import app.models  # noqa: F401,E402  (import for side effects)
from alembic import context
from app.core.config import settings
from app.db.base import Base
from sqlalchemy import engine_from_config, pool

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emit SQL)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=settings.is_sqlite,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=settings.is_sqlite,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
