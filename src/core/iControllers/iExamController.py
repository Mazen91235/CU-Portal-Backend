from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.examDtos import ExamCreateDto, ExamUpdateDto, ExamSearchDto


class IExamController(
    ICrudController[ExamCreateDto, ExamUpdateDto, ExamSearchDto],
):
    pass
