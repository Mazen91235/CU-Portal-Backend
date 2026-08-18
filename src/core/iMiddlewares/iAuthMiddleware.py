from abc import ABC, abstractmethod
from fastapi import Request


class IAuthMiddleware(ABC):
    @abstractmethod
    async def is_logged_in(self, request: Request) -> None:
        pass

    @abstractmethod
    async def is_logged_out(self, request: Request) -> None:
        pass

    @abstractmethod
    async def is_authorized(self, request: Request, *permissions) -> None:
        pass

    @abstractmethod
    async def is_ready(self, request: Request):
        pass