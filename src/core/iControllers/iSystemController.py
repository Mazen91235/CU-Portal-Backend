from abc import ABC, abstractmethod
from fastapi import Request, Response


class ISystemController(ABC):
    @abstractmethod
    async def health_check(self, request: Request) -> Response:
        pass
