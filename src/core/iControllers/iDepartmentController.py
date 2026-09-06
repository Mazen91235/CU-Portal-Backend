from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.departmentDtos import (
    DepartmentCreateDto,
    DepartmentUpdateDto,
    DepartmentSearchDto,
)


class IDepartmentController(
    ICrudController[DepartmentCreateDto, DepartmentUpdateDto, DepartmentSearchDto]
):
    pass
