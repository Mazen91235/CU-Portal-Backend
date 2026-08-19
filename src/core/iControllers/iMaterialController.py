from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController


class IMaterialController(
    IQueryableController, ICreatableController, IUpdatableController
):
    @abstractmethod
    async def delete_many(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_parents(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def copy_many(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def move_many(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def fetch_materials_from_drive(self, request: Request) -> Response:
        pass
