from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController


class IEventController(
    ICrudController,
):
    @abstractmethod
    async def register(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def unregister(self, request: Request) -> Response:
        pass
