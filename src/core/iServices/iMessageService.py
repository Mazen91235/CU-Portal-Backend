from abc import abstractmethod

from core.iServices.bases.iQueryableService import IQueryableService
from core.entities.message import Message
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.messageDtos import MessageSearchDto


class IMessageService(IQueryableService[Message, MessageSearchDto]):
    @abstractmethod
    async def create(self, data: Message) -> BaseResponseDto[Message]:
        pass
