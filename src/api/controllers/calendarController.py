from typing import cast
from core.iControllers.iCalendarController import ICalendarController
from core.iServices.iCalendarService import ICalendarService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.dtos.calendarDtos import CalendarSearchDto


class CalendarController(ICalendarController):
    def __init__(self, calendar_service: ICalendarService, logger: IBaseLogger):
        self.calendar_service = calendar_service
        self.logger = logger

    # Calendar Specific Functions
    async def get_calendar_events(self, request, date_from, date_to):
        try:
            query = Generator[CalendarSearchDto].generate(
                CalendarSearchDto,
                {
                    "date_from": TimezoneHandler.from_isoformat(date_from),
                    "date_to": TimezoneHandler.from_isoformat(date_to),
                },
            )
            response = await self.calendar_service.get_calendar_events(query)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                await self.logger.log(
                    action="GetCalendarEvents",
                    entity="Calendar",
                    level="info",
                    code=404,
                    message="Calendar events not found",
                    source="CalendarController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Calendar events not found",
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response_data,
            )
        except Exception as e:
            await self.logger.log(
                action="GetCalendarEvents",
                entity="Calendar",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="CalendarController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
