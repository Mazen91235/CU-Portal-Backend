from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController
from core.iControllers.bases.iDeletableController import IDeletableController


class ICrudController(
    IQueryableController,
    ICreatableController,
    IUpdatableController,
    IDeletableController,
):
    pass
