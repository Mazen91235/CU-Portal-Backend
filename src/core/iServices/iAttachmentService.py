from abc import abstractmethod
from core.iServices.bases.iBaseService import IBaseService
from core.dtos.baseDtos import BaseResponseDto


class IAttachmentService(IBaseService):
    @abstractmethod
    async def seed(self) -> BaseResponseDto:
        pass

    @abstractmethod
    async def validate(self, start_idx: int) -> BaseResponseDto[int]:
        pass
