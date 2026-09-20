from fastapi import Request, Response
from abc import abstractmethod
from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.releaseDtos import ReleaseCreateDto, ReleaseUpdateDto, ReleaseSearchDto


class IReleaseController(
    ICrudController[ReleaseCreateDto, ReleaseUpdateDto, ReleaseSearchDto]
):
    @abstractmethod
    async def find_versions(self, request: Request) -> Response:
        pass
