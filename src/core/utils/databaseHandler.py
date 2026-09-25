from dotenv import load_dotenv
import os
import json
from pathlib import Path
from sqlalchemy.pool import NullPool

load_dotenv()  # Load environment variables from .env file


class DatabaseHandler:
    @staticmethod
    def get_db_url():
        # Highest priority: full explicit URL (works for sqlite/postgres/etc.)
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            return database_url

        # Construct the database URL from environment variables
        user = os.environ.get("POSTGRES_USER")
        password = os.environ.get("POSTGRES_PASSWORD")
        host = os.environ.get("POSTGRES_HOST")
        port = os.environ.get("POSTGRES_PORT")
        db = os.environ.get("POSTGRES_DB")

        if all([user, password, host, port, db]):
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}?prepared_statement_cache_size=0"

        # Local/test fallback so the API remains runnable without external infra.
        sqlite_path = os.environ.get("SQLITE_DB_PATH") or str(
            Path(__file__).resolve().parents[3] / "app_local.db"
        )
        normalized_path = Path(sqlite_path).resolve()
        return f"sqlite+aiosqlite:///{normalized_path.as_posix()}"

    @staticmethod
    def get_engine_options(db_url: str | None = None) -> dict:
        resolved_url = db_url or DatabaseHandler.get_db_url()
        if resolved_url.startswith("sqlite"):
            return {}

        # Supabase transaction mode (port 6543) does not support prepared statements
        # and is intended for short-lived connections, so keep NullPool there.
        # Persistent VM deployments should prefer direct/session-mode connections and
        # let SQLAlchemy reuse a small async pool instead.
        is_transaction_pooler = (
            os.environ.get("DB_POOL_MODE", "auto").lower() == "transaction"
            or ":6543/" in resolved_url
            or ":6543?" in resolved_url
        )

        if is_transaction_pooler:
            return {
                "connect_args": {
                    "statement_cache_size": 0,
                    "prepared_statement_cache_size": 0,
                    "prepared_statement_name_func": lambda *args: "",
                },
                "poolclass": NullPool,
                "json_serializer": lambda obj: json.dumps(obj, default=str),
            }

        return {
            "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "5")),
            "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "5")),
            "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "1800")),
            "pool_pre_ping": os.environ.get("DB_POOL_PRE_PING", "true").lower() == "true",
            "pool_use_lifo": True,
            "connect_args": {
                "statement_cache_size": int(os.environ.get("DB_STATEMENT_CACHE_SIZE", "100")),
                "prepared_statement_cache_size": int(
                    os.environ.get("DB_PREPARED_STATEMENT_CACHE_SIZE", "100")
                ),
            },
            "json_serializer": lambda obj: json.dumps(obj, default=str),
        }
