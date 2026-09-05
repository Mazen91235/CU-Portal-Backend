from core.iServices.bases.iCrudService import ICrudService
from core.entities.week import Week
from core.dtos.weekDtos import WeekSearchDto


class IWeekService(ICrudService[Week, WeekSearchDto]):
    pass
