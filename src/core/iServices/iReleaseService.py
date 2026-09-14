from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.release import Release
from core.entities.version import Version
from core.dtos.releaseDtos import ReleaseSearchDto, ReleaseCreateDto, ReleaseUpdateDto
from core.dtos.baseDtos import BaseResponseDto


class IReleaseService(
    IQueryableService[Release, ReleaseSearchDto],
    IDeletableService[Release],
):
    @abstractmethod
    async def find_versions(self) -> BaseResponseDto[list[Version]]:
        pass

    @abstractmethod
    async def create(self, data: ReleaseCreateDto) -> BaseResponseDto[Release]:
        pass

    @abstractmethod
    async def update(self, data: ReleaseUpdateDto) -> BaseResponseDto[Release]:
        pass
