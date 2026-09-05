from abc import abstractmethod
from core.iServices.bases.iCrudService import ICrudService
from core.entities.event import Event
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.eventDtos import EventSearchDto


class IEventService(ICrudService[Event, EventSearchDto]):
    @abstractmethod
    async def register(self, event_id: int) -> BaseResponseDto:
        pass

    @abstractmethod
    async def unregister(self, event_id: int) -> BaseResponseDto:
        pass
