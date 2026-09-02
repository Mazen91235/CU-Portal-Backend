from sqlalchemy import and_
from core.iServices.iNotificationService import INotificationService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.userNotification import UserNotification
from core.entities.notification import Notification
from core.dtos.userNotificationDtos import UserNotificationSearchDto
from core.dtos.baseDtos import BaseResponseDto


class NotificationService(INotificationService):
    def __init__(
        self,
        user_notification_repository: IBaseRepository[UserNotification],
        notification_repository: IBaseRepository[Notification],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.user_notification_repository = user_notification_repository
        self.notification_repository = notification_repository
        self.logger = logger
        self.helper_service = helper_service

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
                [],
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
            if not user_notifications:
                await self.logger.log(
                    action="Find",
                    entity="Notification",
                    level="info",
                    code=404,
                    message="No notifications found for the user",
                    source="NotificationService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="No notifications found for the user",
                )
            notifications = [
                un.notification for un in user_notifications if un.notification
            ]
            for notification, user_notification in zip(
                notifications, user_notifications
            ):
                notification.seen = user_notification.seen
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
