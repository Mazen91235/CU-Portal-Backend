from contextvars import ContextVar
from fastapi import Request

# Define a context variable to hold the current request
request_context: ContextVar[Request] = ContextVar("request_context")