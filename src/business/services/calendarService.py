import asyncio
from sqlalchemy import and_
from core.iServices.iCalendarService import ICalendarService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.task import Task
from core.entities.announcement import Announcement
from core.dtos.calendarDtos import CalendarDayEventDto, CalendarResponseDto
from core.dtos.baseDtos import BaseResponseDto
from core.utils.timezoneHandler import TimezoneHandler


class CalendarService(ICalendarService):
    def __init__(
        self,
        task_repository: IBaseRepository[Task],
        announcement_repository: IBaseRepository[Announcement],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.task_repository = task_repository
        self.announcement_repository = announcement_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.task_repository.begin_transaction()

    async def commit_transaction(self):
        await self.task_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.task_repository.rollback_transaction()

    # CRUD Functions
    async def get_calendar_events(self, query):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="GetCalendarEvents",
                    entity="Calendar",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message=logged_in_user_response.message
                    or "Failed to retrieve logged-in user",
                    source="CalendarService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="GetCalendarEvents",
                    entity="Calendar",
                    level="error",
                    code=401,
                    message="No logged-in user found",
                    source="CalendarService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="No logged-in user found",
                )
            response = await self.task_repository.execute_stored_function(
                "get_user_calendar",
                {
                    "p_user_id": logged_in_user.id,
                    "p_date_from": query.date_from,
                    "p_date_to": query.date_to,
                },
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                await self.logger.log(
                    action="GetCalendarEvents",
                    entity="Calendar",
                    level="info",
                    code=404,
                    message="No calendar events found for the specified date range",
                    source="CalendarService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="No calendar events found for the specified date range",
                )
            tasks = response_data.get("tasks", [])
            exams = response_data.get("exams", [])
            announcements = response_data.get("announcements", [])
            result = {}
            for task in tasks:
                deadline = (
                    TimezoneHandler.from_isoformat(task.get("deadline"))
                    if task.get("deadline")
                    else None
                )
                if deadline:
                    date_str = deadline.strftime("%Y-%m-%d")
                else:
                    continue  # Skip tasks without a valid deadline
                if date_str not in result:
                    result[date_str] = {"tasks": [], "exams": [], "announcements": []}
                result[date_str]["tasks"].append(
                    CalendarDayEventDto(
                        id=task.get("id"),
                        event_type="assignment",
                        title=task.get("name") or "",
                        subject=(
                            task.get("subject", {}).get("name")
                            if task.get("subject")
                            else ""
                        ),
                        due=deadline.strftime("%Y-%m-%d"),
                        location=(
                            task.get("details", {}).get("location", "")
                            if task.get("details")
                            else None
                        ),
                    )
                )
            for exam in exams:
                deadline = (
                    TimezoneHandler.from_isoformat(exam.get("deadline"))
                    if exam.get("deadline")
                    else None
                )
                if deadline:
                    date_str = deadline.strftime("%Y-%m-%d")
                else:
                    continue  # Skip exams without a valid deadline
                if date_str not in result:
                    result[date_str] = {"tasks": [], "exams": [], "announcements": []}
                result[date_str]["exams"].append(
                    CalendarDayEventDto(
                        id=exam.get("id"),
                        event_type="exam",
                        title=exam.get("name") or "",
                        subject=(
                            exam.get("subject", {}).get("name")
                            if exam.get("subject")
                            else ""
                        ),
                        due=deadline.strftime("%Y-%m-%d"),
                        location=(
                            exam.get("details", {}).get("location", "")
                            if exam.get("details")
                            else None
                        ),
                    )
                )
            for announcement in announcements:
                date = (
                    TimezoneHandler.from_isoformat(announcement.get("date"))
                    if announcement.get("date")
                    else None
                )
                if date:
                    date_str = date.strftime("%Y-%m-%d")
                else:
                    continue  # Skip announcements without a valid date
                if date_str not in result:
                    result[date_str] = {"tasks": [], "exams": [], "announcements": []}
                result[date_str]["announcements"].append(
                    CalendarDayEventDto(
                        id=announcement.get("id"),
                        event_type="announcement",
                        title=announcement.get("title") or "",
                        subject=(
                            announcement.get("subject", {}).get("name")
                            if announcement.get("subject")
                            else ""
                        ),
                        due=(date.strftime("%Y-%m-%d") if date else None),
                        location=(
                            announcement.get("details", {}).get("location", "")
                            if announcement.get("details")
                            else None
                        ),
                    )
                )
            result = dict(
                sorted(
                    result.items(),
                    key=lambda x: TimezoneHandler.from_isoformat(f"{x[0]}T00:00:00Z"),
                )
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=CalendarResponseDto(events=result),
                message="Calendar events retrieved successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetCalendarEvents",
                entity="Calendar",
                level="error",
                code=500,
                message="An error occurred while finding calendar events",
                details={"error": repr(ex)},
                source="CalendarService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding calendar events, please try again later",
            )
