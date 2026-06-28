from abc import ABC, abstractmethod
from fastapi import Request, Response


class ICreatableController(ABC):
    @abstractmethod
    async def create(self, request: Request) -> Response:
        pass
