from contextvars import ContextVar
from core.entities.user import User

# Define a context variable to hold the logged-in user
user_context: ContextVar[User] = ContextVar("user_context")