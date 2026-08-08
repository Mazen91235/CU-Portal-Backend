from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.task import Task
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.examDtos import ExamSearchDto, ExamCreateDto, ExamUpdateDto
from core.models.queryModel import QueryModel


class IExamService(
    IQueryableService[Task, ExamSearchDto],
    ICreatableService[Task],
    IUpdatableService[Task],
    IDeletableService[Task],
):
    # Admin Specific Methods
    @abstractmethod
    async def create_exam(self, data: ExamCreateDto) -> BaseResponseDto[Task]:
        pass

    @abstractmethod
    async def update_exam(self, exam_id: int, data: ExamUpdateDto) -> BaseResponseDto[Task]:
        pass

    @abstractmethod
    async def delete_exam(self, exam_id: int) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_exams_admin(self, query: QueryModel[ExamSearchDto]) -> BaseResponseDto[list[Task]]:
        pass

    @abstractmethod
    async def get_exam_admin(self, exam_id: int) -> BaseResponseDto[Task]:
        pass

    # User Specific Methods
    @abstractmethod
    async def get_exams_user(self, query: QueryModel[ExamSearchDto]) -> BaseResponseDto[list[Task]]:
        pass

    @abstractmethod
    async def get_exam_user(self, exam_id: int) -> BaseResponseDto[Task]:
        pass