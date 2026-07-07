from abc import abstractmethod

from fastapi import Request, Response

from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController


class IMessageController(IQueryableController, ICreatableController):
    # Additional Query Functions
    @abstractmethod
    async def search(self, request: Request) -> Response:
        pass
