from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.userCompletion import UserCompletion
from core.dtos.userCompletionDtos import UserCompletionSearchDto


class IUserCompletionService(
    IQueryableService[UserCompletion, UserCompletionSearchDto],
    ICreatableService[UserCompletion],
    IDeletableService[UserCompletion],
):
    pass
