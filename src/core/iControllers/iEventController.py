from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.eventDtos import EventCreateDto, EventUpdateDto, EventSearchDto
from core.dtos.userEventDtos import UserEventActionDto


class IEventController(ICrudController[EventCreateDto, EventUpdateDto, EventSearchDto]):
    @abstractmethod
    async def register(self, request: Request, data: UserEventActionDto) -> Response:
        pass

    @abstractmethod
    async def unregister(self, request: Request, data: UserEventActionDto) -> Response:
        pass
