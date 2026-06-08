from abc import ABC, abstractmethod
from typing import Any, Coroutine
from fastapi import Request
from core.entities.user import User
from core.entities.patient import Patient


class IAuthMiddleware(ABC):
    @abstractmethod
    def is_logged_in(self, request: Request) -> Coroutine[Any, Any, User]:
        pass

    @abstractmethod
    def is_logged_out(self, request: Request) -> Coroutine[Any, Any, None]:
        pass

    @abstractmethod
    def is_logged_in_patient(self, request: Request) -> Coroutine[Any, Any, Patient]:
        pass

    @abstractmethod
    def is_logged_out_patient(self, request: Request) -> Coroutine[Any, Any, None]:
        pass
