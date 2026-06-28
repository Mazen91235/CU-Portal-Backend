from abc import ABC, abstractmethod
from fastapi import Request


class IRequestLimitMiddleware(ABC):
    @abstractmethod
    async def throttle(self, request: Request) -> None:
        pass
