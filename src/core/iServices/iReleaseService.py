from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.release import Release
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.releaseDtos import ReleaseSearchDto, ReleaseCreateDto, ReleaseUpdateDto
from core.models.queryModel import QueryModel


class IReleaseService(
    IQueryableService[Release, ReleaseSearchDto],
    ICreatableService[Release],
    IUpdatableService[Release],
    IDeletableService[Release],
):
    @abstractmethod
    async def create_release(self, data: ReleaseCreateDto) -> BaseResponseDto[Release]:
        pass

    @abstractmethod
    async def update_release(self, release_id: int, data: ReleaseUpdateDto) -> BaseResponseDto[Release]:
        pass

    @abstractmethod
    async def delete_release(self, release_id: int) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_releases(self, query: QueryModel[ReleaseSearchDto]) -> BaseResponseDto[list[Release]]:
        pass

    @abstractmethod
    async def get_release(self, release_id: int) -> BaseResponseDto[Release]:
        pass