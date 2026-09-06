from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.weekDtos import WeekCreateDto, WeekUpdateDto, WeekSearchDto


class IWeekController(ICrudController[WeekCreateDto, WeekUpdateDto, WeekSearchDto]):
    pass
