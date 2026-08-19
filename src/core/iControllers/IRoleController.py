from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController


class IRoleController(IQueryableController, ICreatableController, IUpdatableController):
    # Additional Query Functions
    @abstractmethod
    async def create(self, request: Request) -> Response:
        pass

    # Auth Functions
    @abstractmethod
    async def count_permissions(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def update(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def delete(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_roles(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_role(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def search_roles(self, request: Request) -> Response:
        pass