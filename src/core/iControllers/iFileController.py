from abc import ABC, abstractmethod
from fastapi import Request, Response


class IFileController(ABC):
    @abstractmethod
    async def download(self, request: Request, id: str) -> Response:
        pass
