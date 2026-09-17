import asyncio
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from core.iServices.iNotificationService import INotificationService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.userNotification import UserNotification
from core.entities.notification import Notification
from core.entities.task import Task
from core.entities.event import Event
from core.dtos.baseDtos import BaseResponseDto
from core.utils.timezoneHandler import TimezoneHandler


class NotificationService(INotificationService):
    def __init__(
        self,
        user_notification_repository: IBaseRepository[UserNotification],
        notification_repository: IBaseRepository[Notification],
        task_repository: IBaseRepository[Task],
        event_repository: IBaseRepository[Event],
        logger: IBaseLogger,
        helper_service: IHelperService,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self.user_notification_repository = user_notification_repository
        self.notification_repository = notification_repository
        self.task_repository = task_repository
        self.event_repository = event_repository
        self.logger = logger
        self.helper_service = helper_service
        self.session_factory = session_factory
        self._background_tasks: set[asyncio.Task] = set()

    async def begin_transaction(self):
        await self.notification_repository.begin_transaction()

    async def commit_transaction(self):
        await self.notification_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.notification_repository.rollback_transaction()

    # CRUD Functions
    async def find_one(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
    ):
        raise NotImplementedError("There's no implementation for this method.")

    async def find(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
        page=1,
        limit=50,
    ):
        try:
            includes = includes or []
            if "notification" not in includes:
                includes.append("notification")
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Find",
                    entity="Notification",
                    level="error",
                    code=401,
                    message=f"User is not logged in",
                    details={"error": logged_in_user_response.message},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Find",
                    entity="Notification",
                    level="error",
                    code=401,
                    message=f"User is not logged in",
                    details={"error": "No user data found"},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )
            if not data:
                await self.logger.log(
                    action="Find",
                    entity="Notification",
                    level="error",
                    code=400,
                    message=f"Data is required for finding notifications",
                    details={"error": "No data provided"},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Data is required for finding notifications",
                )
            data.user_id = logged_in_user.id
            predicate = self.helper_service.generate_dynamic_predicate(
                UserNotification,
                data,
                ["user_id", "notification_id"],
                is_and,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                UserNotification, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "UserNotification", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "UserNotification", order_by
            )
            result = await self.user_notification_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
                page,
                limit,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            user_notifications = result.data
            notifications = [
                un.notification for un in (user_notifications or []) if un.notification
            ]
            if not user_notifications or not notifications:
                return BaseResponseDto(
                    success=True, data=[], next_page=result.next_page
                )
            for i in range(len(notifications)):
                notifications[i].seen = user_notifications[i].seen
            return BaseResponseDto(
                success=True, data=notifications, next_page=result.next_page
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Notification",
                level="error",
                code=500,
                message=f"An error occurred while finding notifications",
                details={"error": repr(ex)},
                source="NotificationService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding notifications",
            )

    async def create(self, data):
        try:
            if not data.notification_type or not data.parent_id:
                await self.logger.log(
                    action="Create",
                    entity="Notification",
                    level="error",
                    code=400,
                    message=f"Notification type and parent ID are required for creating a notification",
                    details={"error": "Missing notification_type or parent_id"},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Notification type and parent ID are required for creating a notification",
                )
            await self.helper_service.send_notification(
                notification_type=data.notification_type,
                parent_id=data.parent_id,
                content=data.content,
                url=data.url,
                faculty_id=data.faculty_id,
                department_id=data.department_id,
                year_id=data.year_id,
                subject_id=data.subject_id,
                user_ids=data.user_ids,
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=None,
                message="Notification created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Notification",
                level="error",
                code=500,
                message=f"An error occurred while creating a notification",
                details={"error": repr(ex)},
                source="NotificationService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating a notification",
            )

    # Notification Specific Methods
    async def mark_notification_as_seen(self, notification_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="MarkNotificationAsSeen",
                    entity="Notification",
                    level="error",
                    code=401,
                    message=f"User is not logged in",
                    details={"error": logged_in_user_response.message},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="MarkNotificationAsSeen",
                    entity="Notification",
                    level="error",
                    code=401,
                    message=f"User is not logged in",
                    details={"error": "No user data found"},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )
            user_notification_response = (
                await self.user_notification_repository.find_one(
                    and_(
                        UserNotification.user_id == logged_in_user.id,
                        UserNotification.notification_id == notification_id,
                    )
                )
            )
            if not user_notification_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_notification_response.code,
                    data=None,
                    message=user_notification_response.message,
                )
            user_notification = user_notification_response.data
            if not user_notification:
                await self.logger.log(
                    action="MarkNotificationAsSeen",
                    entity="Notification",
                    level="error",
                    code=404,
                    message=f"User notification not found",
                    details={
                        "error": f"No user notification found for user_id {logged_in_user.id} and notification_id {notification_id}"
                    },
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Notification not found",
                )
            if user_notification.seen:
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=True,
                    message="Notification already marked as seen",
                )
            user_notification.seen = True
            update_response = await self.user_notification_repository.update(
                user_notification, ["seen"]
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            await self.logger.log(
                action="MarkNotificationAsSeen",
                entity="Notification",
                level="info",
                code=200,
                message=f"Notification marked as seen for user_id {logged_in_user.id} and notification_id {notification_id}",
                details={},
                source="NotificationService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Notification marked as seen",
            )
        except Exception as ex:
            await self.logger.log(
                action="MarkNotificationAsSeen",
                entity="Notification",
                level="error",
                code=500,
                message=f"An error occurred while marking notification as seen",
                details={"error": repr(ex)},
                source="NotificationService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while marking notification as seen",
            )

    async def send_reminders(self):
        try:
            task = asyncio.create_task(self._send_reminders())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Reminders sent successfully for tasks, exams, and events.",
            )
        except Exception as ex:
            await self.logger.log(
                action="SendReminders",
                entity="Notification",
                level="error",
                code=500,
                message=f"An error occurred while sending reminders",
                details={"error": repr(ex)},
                source="NotificationService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while sending reminders",
            )

    # Helper Functions
    async def _send_reminders(self):
        async with self.session_factory() as session:
            try:
                await session.begin()
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Task, ["subject"]
                )
                dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                    "Task", ["deadline"]
                )
                tasks_response = await self.task_repository.find(
                    and_(
                        Task.deadline >= TimezoneHandler.now(),
                        Task.deadline <= TimezoneHandler.add_days(3),
                    ),
                    dynamic_includes,
                    order_by=dynamic_order_by,
                    limit=int(1e6),
                )
                if not tasks_response.success:
                    await session.rollback()
                    return BaseResponseDto(
                        success=False,
                        code=tasks_response.code,
                        data=None,
                        message=tasks_response.message,
                    )
                tasks = tasks_response.data or []
                exams = [task for task in tasks if task.task_type == "exam"]
                tasks = [task for task in tasks if task.task_type != "exam"]
                bg_notifications = []
                for task in tasks:
                    due = TimezoneHandler.get_due_as_str(task.deadline)
                    if due is None or task.subject is None:
                        continue
                    content = f"Reminder: Task '{task.name}' for subject '{task.subject.name}' is due in {due}."
                    share_link = f"/user/tasks/{task.id}"
                    response = await self.helper_service.send_notification(
                        notification_type=Notification.NotificationType.TASK,
                        parent_id=task.id,
                        content=content,
                        url=share_link,
                        subject_id=task.subject_id,
                    )
                    if response.success and response.data is not None:
                        bg_notifications.append(response.data)
                for exam in exams:
                    due = TimezoneHandler.get_due_as_str(exam.deadline)
                    if due is None or exam.subject is None:
                        continue
                    content = f"Reminder: Exam '{exam.name}' for subject '{exam.subject.name}' is due in {due}."
                    share_link = f"/user/exams/{exam.id}"
                    response = await self.helper_service.send_notification(
                        notification_type=Notification.NotificationType.EXAM,
                        parent_id=exam.id,
                        content=content,
                        url=share_link,
                        subject_id=exam.subject_id,
                    )
                    if response.success and response.data is not None:
                        bg_notifications.append(response.data)
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Event, ["user_events"]
                )
                dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                    "Event", ["start_date"]
                )
                events_response = await self.event_repository.find(
                    and_(
                        Event.start_date >= TimezoneHandler.now(),
                        Event.start_date <= TimezoneHandler.add_days(3),
                    ),
                    dynamic_includes,
                    order_by=dynamic_order_by,
                    limit=int(1e6),
                )
                if not events_response.success:
                    await session.rollback()
                    return BaseResponseDto(
                        success=False,
                        code=events_response.code,
                        data=None,
                        message=events_response.message,
                    )
                events = events_response.data or []
                for event in events:
                    due = TimezoneHandler.get_due_as_str(event.start_date)
                    if due is None:
                        continue
                    content = f"Reminder: Event '{event.title}' that you registered for is scheduled to start in {due}."
                    share_link = f"/user/events/{event.id}"
                    user_ids = {ue.user_id for ue in event.user_events}
                    response = await self.helper_service.send_notification(
                        notification_type=Notification.NotificationType.EVENT,
                        parent_id=event.id,
                        content=content,
                        url=share_link,
                        user_ids=user_ids,
                    )
                    if response.success and response.data is not None:
                        bg_notifications.append(response.data)
                await session.commit()
                await asyncio.gather(*bg_notifications, return_exceptions=True)
                await self.logger.log(
                    action="BackgroundSendReminders",
                    entity="Notification",
                    level="info",
                    code=200,
                    message=f"Reminders sent successfully for tasks, exams, and events.",
                    details={},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=None,
                    message="Reminders sent successfully for tasks, exams, and events.",
                )
            except Exception as ex:
                await session.rollback()
                await self.logger.log(
                    action="BackgroundSendReminders",
                    entity="Notification",
                    level="error",
                    code=500,
                    message=f"An error occurred while sending reminders",
                    details={"error": repr(ex)},
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while sending reminders",
                )
            finally:
                try:
                    await session.close()
                except Exception:
                    pass
