from abc import ABC, abstractmethod
from fastapi import Request, Response


class IFileController(ABC):
    @abstractmethod
    async def download_file(self, request: Request) -> Response:
        pass
