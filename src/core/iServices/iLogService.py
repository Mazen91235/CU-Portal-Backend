from core.iServices.bases.iQueryableService import IQueryableService
from core.entities.log import Log
from core.dtos.logDtos import LogSearchDto


class ILogService(IQueryableService[Log, LogSearchDto]):
    pass
