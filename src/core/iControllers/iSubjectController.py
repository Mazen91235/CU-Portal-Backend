from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController
from core.iControllers.bases.iDeletableController import IDeletableController

class ISubjectController(IQueryableController, ICreatableController, IUpdatableController,IDeletableController,):
  # Additional Query Functions
    @abstractmethod
    async def search(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def register(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def unregister(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_enrolled(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_available(self, request: Request) -> Response:
        pass
    
    @abstractmethod
    async def search_registered(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_enrolled_one(self, request: Request) -> Response:
        pass