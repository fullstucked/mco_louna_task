import sys
import os
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Alembic config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Pull DB URL from environment

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../" * 4))
sys.path.append(PROJECT_ROOT)


from payments.infrastructure.database.session import metadata  # noqa: E402
from payments.infrastructure.database.payments.table import payments  # noqa: E402
from payments.infrastructure.database.outbox.table import outbox  # noqa: E402

target_metadata = metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode (sync SQL strings only)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode using AsyncEngine."""
    # pyrefly: ignore [bad-argument-type]
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))
    connectable = create_async_engine(
        # pyrefly: ignore [bad-argument-type]
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Alembic expects a synchronous connection, so we use run_sync
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    """The synchronous function Alembic calls on Async connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
