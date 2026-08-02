from core.iServices.bases.iCrudService import ICrudService
from core.entities.department import Department
from core.dtos.departmentDtos import DepartmentSearchDto


class IDepartmentService(ICrudService[Department, DepartmentSearchDto]):
    pass
