from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.dtos.messageDtos import MessageCreateDto, MessageSearchDto


class IMessageController(
    IQueryableController[MessageSearchDto], ICreatableController[MessageCreateDto]
):
    pass
