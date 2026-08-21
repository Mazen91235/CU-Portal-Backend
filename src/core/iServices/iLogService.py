from abc import abstractmethod
from core.iServices.bases.iCountableService import ICountableService
from core.iServices.bases.iQueryableService import IQueryableService
from core.entities.log import Log
from core.dtos.logDtos import LogSearchDto
from core.dtos.baseDtos import BaseResponseDto


class ILogService(
    ICountableService[LogSearchDto], IQueryableService[Log, LogSearchDto]
):
    @abstractmethod
    async def delete(self, logs_count: int) -> BaseResponseDto[bool]:
        pass
