from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.role import Role
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.roleDtos import RoleCreateDto, RoleUpdateDto, RoleSearchDto


class IRoleService(
    IQueryableService[Role, RoleSearchDto],
    ICreatableService[Role],
    IDeletableService[Role],
):
    @abstractmethod
    async def update(self, id: int, data: RoleUpdateDto) -> BaseResponseDto[Role]:
        pass

    @abstractmethod
    async def count_permissions(self) -> BaseResponseDto[int]:
        pass

    @abstractmethod
    async def get_permissions(self) -> BaseResponseDto[list[str]]:
        pass

    @abstractmethod
    async def reset_permissions(self) -> BaseResponseDto:
        pass
