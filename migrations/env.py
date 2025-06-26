import asyncio
import ssl
from logging.config import fileConfig
from threading import Thread
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Import your models / metadata
from ehp.config import settings
from ehp.core.models.db import *
from ehp.db import Base

# The target metadata for 'autogenerate'
target_metadata = Base.metadata

db_url_escaped = settings.SQLALCHEMY_ASYNC_DATABASE_URI.replace("%", "%%")

config.set_main_option("sqlalchemy.url", db_url_escaped)

# ---- SSL SETUP (for AWS RDS or any SSL-enabled Postgres) ----
# 2) Create an SSL context if your server requires certificate verification
ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

# If using Amazon RDS, download rds-combined-ca-bundle.pem from AWS docs
# ssl_context.load_verify_locations("rds-combined-ca-bundle.pem")

# Enforce hostname checks & require valid certs
# ssl_context.check_hostname = True
# ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# ----------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    In offline mode, Alembic does not create an actual DB connection,
    so 'connect_args' or SSL config won't matter here.
    """
    url = config.get_main_option("sqlalchemy.url")

    # Offline mode: no real DB connection is made
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # We typically do NOT pass connect_args here, as it has no effect offline
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Helper that configures the migration context using an existing connection."""
    
    def process_revision_directives(context, revision, directives):
        """Process revision directives to disable empty migrations in autogenerate."""
        if config.cmd_opts.autogenerate:
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                print("No changes in schema detected.")

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_revision_directives=process_revision_directives,
        # No need for connect_args here, because we've already created
        # the Engine/Connection with SSL in async_engine_from_config.
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode, creating an async engine that uses SSL."""

    # 3) Pass the SSL context as a connect_arg for asyncpg
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # The key line for SSL: pass the SSL context to asyncpg
        connect_args={"ssl": ssl_context},
    )

    async with connectable.connect() as connection:
        # This runs your synchronous do_run_migrations in a thread-safe manner
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_async_with_new_loop(coro: Any) -> None:
    """Run an async coroutine in a new event loop in a separate thread."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a separate thread."""
    thread = Thread(target=run_async_with_new_loop, args=(run_async_migrations(),))
    thread.start()
    thread.join()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
