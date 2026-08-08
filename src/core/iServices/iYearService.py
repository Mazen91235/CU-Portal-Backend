from core.iServices.bases.iCrudService import ICrudService
from core.entities.year import Year
from core.dtos.yearDtos import YearSearchDto


class IYearService(ICrudService[Year, YearSearchDto]):
    pass
