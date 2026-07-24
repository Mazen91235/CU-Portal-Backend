from abc import abstractmethod
from fastapi import Request, Response

from core.iControllers.bases.iCrudController import ICrudController


class IDepartmentController(ICrudController):
    @abstractmethod
    async def search(self, request: Request) -> Response:
        pass
