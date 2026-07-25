from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController


class IFacultyController(ICrudController):
    # Additional Query Functions
    @abstractmethod
    async def search(self, request: Request) -> Response:
        pass
