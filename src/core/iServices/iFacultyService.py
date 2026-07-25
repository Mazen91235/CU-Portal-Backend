from core.iServices.bases.iCrudService import ICrudService
from core.entities.faculty import Faculty
from core.dtos.facultyDtos import FacultySearchDto


class IFacultyService(ICrudService[Faculty, FacultySearchDto]):
    pass
