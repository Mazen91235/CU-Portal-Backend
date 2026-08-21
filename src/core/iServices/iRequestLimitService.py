from abc import abstractmethod
from core.iServices.bases.iCountableService import ICountableService
from core.dtos.requestLimitDtos import RequestLimitSearchDto
from core.dtos.baseDtos import BaseResponseDto


class IRequestLimitService(ICountableService[RequestLimitSearchDto]):
    @abstractmethod
    async def create(
        self, ip: str | None, route: str | None, user_id: int | None
    ) -> BaseResponseDto[bool]:
        pass
