#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from alembic.config import Config
from alembic import command


async def migrate():
    # Programmatic config
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", "sqlite+aiosqlite:///./students_portal.db")

    # Generate migrations (uncomment when needed)
    # command.revision(alembic_cfg, autogenerate=True, message="Your message")

    # Run migrations
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())