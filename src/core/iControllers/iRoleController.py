from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.roleDtos import RoleCreateDto, RoleUpdateDto, RoleSearchDto


class IRoleController(ICrudController[RoleCreateDto, RoleUpdateDto, RoleSearchDto]):
    @abstractmethod
    async def count_permissions(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_permissions(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def reset_permissions(self, request: Request) -> Response:
        pass
