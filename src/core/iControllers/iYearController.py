from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.yearDtos import YearCreateDto, YearUpdateDto, YearSearchDto


class IYearController(ICrudController[YearCreateDto, YearUpdateDto, YearSearchDto]):
    pass
