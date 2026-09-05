from abc import ABC, abstractmethod
from fastapi import Request, Response


class ICalendarController(ABC):
    @abstractmethod
    async def get_calendar_events(
        self, request: Request, date_from: str, date_to: str
    ) -> Response:
        pass
