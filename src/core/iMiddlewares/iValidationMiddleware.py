from abc import ABC, abstractmethod
from fastapi import Request
from typing import Any, Coroutine


class IValidationMiddleware(ABC):
    @abstractmethod
    def handle(self, request: Request, *keys) -> Coroutine[Any, Any, None]:
        pass

    @abstractmethod
    def validate_files_count(
        self, request: Request, expected_count: int
    ) -> Coroutine[Any, Any, None]:
        pass
