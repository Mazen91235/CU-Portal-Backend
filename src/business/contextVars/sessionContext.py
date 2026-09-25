from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

# Holds the active request-scoped database session when one is needed.
session_context: ContextVar[AsyncSession | None] = ContextVar(
    "session_context", default=None
)
