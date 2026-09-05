from abc import ABC, abstractmethod
from core.dtos.calendarDtos import CalendarSearchDto, CalendarResponseDto
from core.dtos.baseDtos import BaseResponseDto


class ICalendarService(ABC):
    @abstractmethod
    async def get_calendar_events(
        self, query: CalendarSearchDto
    ) -> BaseResponseDto[CalendarResponseDto]:
        pass
