from abc import ABC, abstractmethod
from fastapi import Request, Response


class IUpdatableController(ABC):
    @abstractmethod
    async def update(self, request: Request) -> Response:
        pass
