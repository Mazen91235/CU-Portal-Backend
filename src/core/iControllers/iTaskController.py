from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.taskDtos import TaskCreateDto, TaskUpdateDto, TaskSearchDto


class ITaskController(ICrudController[TaskCreateDto, TaskUpdateDto, TaskSearchDto]):
    pass
