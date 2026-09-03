from abc import ABC, abstractmethod
from fastapi import Request, Response


class IAttachmentController(ABC):
    @abstractmethod
    async def seed(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def validate(self, request: Request, start_idx: int) -> Response:
        pass
