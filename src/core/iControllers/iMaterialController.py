from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController
from core.dtos.materialDtos import (
    MaterialCreateDto,
    MaterialUpdateDto,
    MaterialSearchDto,
    MaterialsCopyOrMoveDto,
    MaterialsFetchFromDriveDto,
    MaterialDownloadManyDto,
)


class IMaterialController(
    IQueryableController[MaterialSearchDto],
    ICreatableController[MaterialCreateDto],
    IUpdatableController[MaterialUpdateDto],
):
    @abstractmethod
    async def delete_many(self, request: Request, ids: list[int]) -> Response:
        pass

    @abstractmethod
    async def get_parents(self, request: Request, id: int) -> Response:
        pass

    @abstractmethod
    async def copy_many(
        self, request: Request, data: MaterialsCopyOrMoveDto
    ) -> Response:
        pass

    @abstractmethod
    async def move_many(
        self, request: Request, data: MaterialsCopyOrMoveDto
    ) -> Response:
        pass

    @abstractmethod
    async def fetch_materials_from_drive(
        self, request: Request, data: MaterialsFetchFromDriveDto
    ) -> Response:
        pass

    @abstractmethod
    async def download_many(
        self, request: Request, data: MaterialDownloadManyDto
    ) -> Response:
        pass
