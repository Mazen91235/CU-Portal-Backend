from abc import ABC, abstractmethod
from fastapi import Request


class IValidationMiddleware(ABC):
    @abstractmethod
    async def validate(self, request: Request, *keys) -> None:
        pass
