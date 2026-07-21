from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.entities.material import Material
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.materialDtos import (
    MaterialExtendedResponseDto,
    MaterialResponseDto,
    MaterialMinimalResponseDto,
    MaterialsCopyAndMoveRequest,
    DriveMaterialPreviewDto,
)


class IMaterialService(
    IQueryableService[Material, None],
    IUpdatableService[Material],
):
    @abstractmethod
    async def create(self, data: Material) -> BaseResponseDto[MaterialResponseDto]:
        pass

    @abstractmethod
    async def delete_many(self, ids: list[int]) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_by_id(
        self, material_id: int
    ) -> BaseResponseDto[MaterialExtendedResponseDto]:
        pass

    @abstractmethod
    async def get_detail(
        self, material_id: int
    ) -> BaseResponseDto[MaterialResponseDto]:
        pass

    @abstractmethod
    async def get_parents(
        self, material_id: int
    ) -> BaseResponseDto[list[MaterialMinimalResponseDto]]:
        pass

    @abstractmethod
    async def move_many(
        self, data: MaterialsCopyAndMoveRequest
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def copy_many(
        self, data: MaterialsCopyAndMoveRequest
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def fetch_one_material_from_drive(
        self, data
    ) -> BaseResponseDto[DriveMaterialPreviewDto]:
        pass

    @abstractmethod
    async def fetch_materials_from_drive(
        self, data: DriveMaterialPreviewDto
    ) -> BaseResponseDto[MaterialResponseDto]:
        pass
