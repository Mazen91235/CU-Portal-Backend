from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iDeletableController import IDeletableController
from core.dtos.userCompletionDtos import UserCompletionCreateDto, UserCompletionSearchDto


class IUserCompletionController(
    IQueryableController[UserCompletionSearchDto],
    ICreatableController[UserCompletionCreateDto],
    IDeletableController,
):
    pass
