from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.facultyDtos import FacultyCreateDto, FacultyUpdateDto, FacultySearchDto


class IFacultyController(
    ICrudController[FacultyCreateDto, FacultyUpdateDto, FacultySearchDto]
):
    pass
