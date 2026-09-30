from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.entities.material import Material
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.materialDtos import (
    MaterialsDeleteDto,
    MaterialSearchDto,
    MaterialCreateDto,
    MaterialUpdateDto,
    MaterialsCopyOrMoveDto,
    MaterialsFetchFromDriveDto,
    MaterialDownloadManyDto,
)


class IMaterialService(
    IQueryableService[Material, MaterialSearchDto],
):
    @abstractmethod
    async def create(self, data: MaterialCreateDto) -> BaseResponseDto[Material]:
        pass

    @abstractmethod
    async def update(self, data: MaterialUpdateDto) -> BaseResponseDto[Material]:
        pass

    @abstractmethod
    async def delete_many(self, data: MaterialsDeleteDto) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_parents(self, material_id: int) -> BaseResponseDto[list[Material]]:
        pass

    @abstractmethod
    async def move_many(self, data: MaterialsCopyOrMoveDto) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def copy_many(self, data: MaterialsCopyOrMoveDto) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def fetch_materials_from_drive(
        self, data: MaterialsFetchFromDriveDto
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def download_many(
        self, data: MaterialDownloadManyDto
    ) -> BaseResponseDto:
        pass
