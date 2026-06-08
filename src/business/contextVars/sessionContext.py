from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

# Holds the active request-scoped database session.
session_context: ContextVar[AsyncSession | None] = ContextVar(
    "session_context", default=None
)
