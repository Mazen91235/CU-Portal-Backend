from abc import abstractmethod
from core.iServices.bases.iCrudService import ICrudService
from core.entities.event import Event
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.eventDtos import EventSearchDto
from core.dtos.userEventDtos import (UserEventRegisterDto,UserEventUnregisterDto)



class IEventService(ICrudService[Event, EventSearchDto]):
    @abstractmethod
    async def register(self, data: UserEventRegisterDto) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def unregister(self, data: UserEventUnregisterDto) -> BaseResponseDto[bool]:
        pass
