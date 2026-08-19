from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController


class IRoleController(ICrudController):
    @abstractmethod
    async def count_permissions(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def reset_permissions(self, request: Request) -> Response:
        pass
