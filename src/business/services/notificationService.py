from sqlalchemy import and_
from sqlalchemy.orm import selectinload
from core.iServices.iNotificationService import INotificationService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.userNotification import UserNotification
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.notificationDtos import NotificationSearchDto
from core.models.queryModel import QueryModel


class NotificationService(INotificationService):
    def __init__(
        self,
        user_notification_repository: IBaseRepository[UserNotification],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.user_notification_repository = user_notification_repository
        self.logger = logger
        self.helper_service = helper_service

    # Generic Methods
    async def find_one(self, predicate=None, includes=None, selects=None, order_by=None, descending=False):
        return await self.user_notification_repository.find_one(predicate, includes, selects, order_by, descending)

    async def find(self, predicate=None, includes=None, selects=None, order_by=None, descending=False, page=1, limit=50):
        return await self.user_notification_repository.find(predicate, includes, selects, order_by, descending, page, limit)

    async def count(self, predicate=None):
        return await self.user_notification_repository.count(predicate)

    # User Specific Methods
    async def get_notifications_user(self, query: QueryModel[NotificationSearchDto]) -> BaseResponseDto[list[UserNotification]]:
        try:
            current_user_response = await self.helper_service.get_logged_in_user()
            if not current_user_response.success:
                return BaseResponseDto(success=False, code=current_user_response.code, message=current_user_response.message)
            current_user = current_user_response.data

            # Base condition to only get the current user's notifications
            conditions = [UserNotification.user_id == current_user.id]

            # Seen filter
            if query.data.seen is not None:
                conditions.append(UserNotification.seen == query.data.seen)

            final_predicate = and_(*conditions)

            # Resolve Dynamic Includes
            includes = self.helper_service.generate_dynamic_includes(UserNotification, query.includes)
            
            # Default include to ensure the actual Notification is returned alongside the link
            if not includes:
                includes = [selectinload(UserNotification.notification)]

            # Default ordering
            order_by = self.helper_service.generate_dynamic_order_by("UserNotification", query.order_by)
            if not order_by:
                order_by = [UserNotification.created_at]
                query.descending = True

            result = await self.user_notification_repository.find(
                predicate=final_predicate,
                includes=includes,
                order_by=order_by,
                descending=query.descending,
                page=query.page,
                limit=query.limit,
            )

            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )

            return BaseResponseDto(
                success=True, 
                code=200, 
                data=result.data, 
                message="Notifications retrieved successfully."
            )

        except Exception as ex:
            await self.logger.log("Get", "Notification", "error", 500, "Error fetching user notifications", "NotificationService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while fetching your notifications.")

    async def mark_notification_as_seen(self, notification_id: int) -> BaseResponseDto[bool]:
        try:
            current_user_response = await self.helper_service.get_logged_in_user()
            if not current_user_response.success:
                return BaseResponseDto(success=False, code=current_user_response.code, message=current_user_response.message)
            current_user = current_user_response.data

            # Find the table record linking the user to the notification
            result = await self.user_notification_repository.find_one(
                and_(
                    UserNotification.notification_id == notification_id,
                    UserNotification.user_id == current_user.id
                )
            )

            if not result.success or not result.data:
                return BaseResponseDto(success=False, code=404, message="Notification not found.")

            user_notification = result.data
            
            # Only update if it actually needs to be updated
            if not user_notification.seen:
                user_notification.seen = True
                update_result = await self.user_notification_repository.update(user_notification, ["seen"])
                
                if not update_result.success:
                    return BaseResponseDto(success=False, code=update_result.code, message=update_result.message)

            await self.logger.log(
                action="Mark",
                entity="Notification",
                level="info",
                code=200,
                message="Notification Marked as Seen Successfully.",
                source="NotificationService",
                details={"notification_id": notification_id}
            )

            return BaseResponseDto(success=True, code=200, data=True, message="Notification marked as seen successfully.")

        except Exception as ex:
            await self.logger.log("Mark", "Notification", "error", 500, "Error marking notification as seen", "NotificationService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while updating the notification.")