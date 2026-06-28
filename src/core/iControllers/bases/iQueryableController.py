from abc import ABC, abstractmethod
from fastapi import Request, Response


class IQueryableController(ABC):
    @abstractmethod
    async def find_one(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def find(self, request: Request) -> Response:
        pass
