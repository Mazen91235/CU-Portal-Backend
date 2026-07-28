from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.entities.message import Message
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.messageDtos import MessageSearchDto


class IMessageService(IQueryableService[Message, MessageSearchDto],ICreatableService[Message]):
    pass
