from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController
from core.iControllers.bases.iDeletableController import IDeletableController


class IAnnouncementController(IQueryableController, ICreatableController,  IUpdatableController, IDeletableController):
    # Additional Query Functions
    @abstractmethod
    async def search(self, request: Request) -> Response:
        
        pass