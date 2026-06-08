import asyncio
import os
import sys
from pathlib import Path
from logging.config import dictConfig

from dotenv import load_dotenv
from sqlalchemy import pool, DateTime, Float, Numeric, TIMESTAMP
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from alembic.autogenerate import renderers
from sqlalchemy.dialects import postgresql

# Ensure src is importable when Alembic executes from repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.entities.base import Base


load_dotenv()

# Alembic Config object
config = context.config

# Configure logging
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "%(levelname)s %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }
)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Alembic online mode in this project uses async engine; ensure asyncpg driver.
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "alzheimers_db")

    DATABASE_URL = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Target metadata
target_metadata = Base.metadata


# --- Force PostgreSQL types in migrations ---
@renderers.dispatch_for(DateTime)
def _render_datetime(type_, autogen_context):
    return f"postgresql.TIMESTAMP(timezone={getattr(type_, 'timezone', False)})"


@renderers.dispatch_for(Float)
def _render_float(type_, autogen_context):
    return "postgresql.DOUBLE_PRECISION"


@renderers.dispatch_for(Numeric)
def _render_numeric(type_, autogen_context):
    if type_.precision is not None and type_.scale is not None:
        return f"postgresql.NUMERIC(precision={type_.precision}, scale={type_.scale})"
    return "postgresql.NUMERIC"


# --- Migration runners ---
def _compare_type(
    context, inspected_column, metadata_column, inspected_type, metadata_type
):
    # Treat DateTime, TIMESTAMP, and postgresql.TIMESTAMP as equivalent for autogenerate
    types = (DateTime, TIMESTAMP, postgresql.TIMESTAMP)
    if isinstance(inspected_type, types) and isinstance(metadata_type, types):
        return False
    return None


def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        process_compare_type=_compare_type,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_compare_type=_compare_type,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in 'online' (async) mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
        url=DATABASE_URL,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online():
    """Run async migrations with asyncio event loop."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_async_migrations())


# --- Entrypoint ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# No changes needed. Already handles PostgreSQL types and avoids DATETIME/TIMESTAMP migration issues.
