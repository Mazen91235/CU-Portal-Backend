from core.iControllers.bases.iQueryableController import IQueryableController
from core.dtos.logDtos import LogSearchDto


class ILogController(IQueryableController[LogSearchDto]):
    pass
