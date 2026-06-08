from typing import TypeVar, Generic
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.iServices.bases.iDeletableService import IDeletableService

T = TypeVar("T")  # Entity Type
U = TypeVar("U")  # EntitySearchDto Type


class ICrudService(
    Generic[T, U],
    IQueryableService[T, U],
    ICreatableService[T],
    IUpdatableService[T],
    IDeletableService[T],
):
    pass
