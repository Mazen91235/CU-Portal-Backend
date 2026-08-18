from core.iServices.bases.iCrudService import ICrudService
from core.entities.task import Task
from core.dtos.taskDtos import TaskSearchDto


class ITaskService(ICrudService[Task, TaskSearchDto]):
    pass