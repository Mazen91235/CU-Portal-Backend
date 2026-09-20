from abc import ABC, abstractmethod
from fastapi import Request


class IValidationMiddleware(ABC):
    @abstractmethod
    async def validate(self, request: Request, *keys) -> None:
        pass

    @abstractmethod
    async def validate_details_numbers(self, request: Request, *keys) -> None:
        pass

    @abstractmethod
    async def validate_api_key(self, request: Request) -> None:
        pass
