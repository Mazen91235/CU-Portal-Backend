from contextvars import ContextVar

# Define a context variable to hold the logged-in user's permissions
permissions_context: ContextVar[set[str]] = ContextVar("permissions_context")
