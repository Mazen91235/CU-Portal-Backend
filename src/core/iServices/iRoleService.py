from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.role import Role
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.roleDtos import (
    RoleResponseDto,
    AddRoleDto,
    updateRoleDto
)


class IRoleService(
    IQueryableService[Role],
    IUpdatableService[Role],
    ICreatableService[Role],
    IDeletableService[Role]
):
    @abstractmethod
    async def create(self, data: AddRoleDto) -> BaseResponseDto[RoleResponseDto]:
        pass

    @abstractmethod
    async def update(self, data: updateRoleDto) -> BaseResponseDto[RoleResponseDto]:
        pass

    @abstractmethod
    async def delete(self, role_id: int) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_role(self, role_id: int) -> BaseResponseDto[RoleResponseDto]:
        pass

    @abstractmethod
    async def search_roles(self, query: str) -> BaseResponseDto[list[RoleResponseDto]]:
        pass

    @abstractmethod
    async def get_all(self) -> BaseResponseDto[list[RoleResponseDto]]:
        pass

    @abstractmethod
    async def count_permissions(self) -> BaseResponseDto[int]:
        pass
