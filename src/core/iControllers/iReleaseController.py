from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.releaseDtos import ReleaseCreateDto, ReleaseUpdateDto, ReleaseSearchDto


class IReleaseController(
    ICrudController[ReleaseCreateDto, ReleaseUpdateDto, ReleaseSearchDto]
):
    pass
