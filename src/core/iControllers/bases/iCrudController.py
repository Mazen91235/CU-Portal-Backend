from typing import TypeVar, Generic
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController
from core.iControllers.bases.iDeletableController import IDeletableController

C = TypeVar("C")  # EntityCreateDto
U = TypeVar("U")  # EntityUpdateDto
S = TypeVar("S")  # EntitySearchDto


class ICrudController(
    Generic[C, U, S],
    IQueryableController[S],
    ICreatableController[C],
    IUpdatableController[U],
    IDeletableController,
):
    pass
