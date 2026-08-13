from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController
from core.iControllers.bases.iDeletableController import IDeletableController


class IReleaseController(
    IQueryableController, 
    ICreatableController, 
    IUpdatableController,
    IDeletableController
):
    @abstractmethod
    async def create_release(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def update_release(self, request: Request, release_id: int) -> Response:
        pass

    @abstractmethod
    async def delete_release(self, request: Request, release_id: int) -> Response:
        pass

    @abstractmethod
    async def get_releases(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_release(self, request: Request, release_id: int) -> Response:
        pass