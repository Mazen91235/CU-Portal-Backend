from abc import ABC, abstractmethod
from fastapi import Request, Response


class IDeletableController(ABC):
    @abstractmethod
    async def delete(self, request: Request, id: int) -> Response:
        pass
