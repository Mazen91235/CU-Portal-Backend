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
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

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
        return {
            "connect_args": {
                "statement_cache_size": 0,
            },
            "prepared_statement_cache_size": 0,  # Required for Transaction Pooler
            "poolclass": NullPool,  # Use NullPool for asyncpg to avoid connection issues
            "json_serializer": lambda obj: json.dumps(obj, default=str),
        }
