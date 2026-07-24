from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.entities.task import Task
from core.entities.user import User
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.taskDtos import (
    TaskCreateDto,
    TaskUpdateDto,
    TaskResponseDto,
    TaskSearchDto,
)


class ITaskService(
    IQueryableService[Task, TaskSearchDto],
    IUpdatableService[Task],
):
    @abstractmethod
    async def create(self, data: TaskCreateDto) -> BaseResponseDto[TaskResponseDto]:
        pass

    @abstractmethod
    async def update(self, task_id: int, data: TaskUpdateDto) -> BaseResponseDto[TaskResponseDto]:
        pass

    @abstractmethod
    async def delete(self, task_id: int) -> BaseResponseDto[bool]:
        pass