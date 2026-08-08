from core.iServices.bases.iCrudService import ICrudService
from core.entities.task import Task
from core.dtos.examDtos import ExamSearchDto


class IExamService(
    ICrudService[Task, ExamSearchDto],
):
    pass
