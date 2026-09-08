from core.iControllers.iNotificationController import INotificationController
from core.iServices.iNotificationService import INotificationService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.notification import Notification
from core.dtos.userNotificationDtos import (
    UserNotificationSearchDto,
)
from core.dtos.notificationDtos import (
    NotificationCreateDto,
    NotificationResponseDto,
)


class NotificationController(INotificationController):
    def __init__(self, notification_service: INotificationService, logger: IBaseLogger):
        self.notification_service = notification_service
        self.logger = logger

    async def find_one(self, request, id):
        raise NotImplementedError("There's no implementation for this method.")

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[
                UserNotificationSearchDto
            ].generate_from_query(UserNotificationSearchDto, query)
            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.notification_service.find(
                entity_search_dto,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            notifications = response.data

            notifications_mapped = Mapper[
                Notification, NotificationResponseDto
            ].map_list(notifications or [], NotificationResponseDto, True)

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=notifications_mapped,
                next_page=response.next_page,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Notification",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="NotificationController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.notification_service.begin_transaction()
            notification = Mapper[NotificationCreateDto, Notification].map(
                data, Notification
            )
            response = await self.notification_service.create(notification)

            if not response.success:
                await self.notification_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.notification_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                message="Notification created successfully",
            )
        except Exception as e:
            await self.notification_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Notification",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="NotificationController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def mark_notification_as_seen(self, request, id):
        try:
            await self.notification_service.begin_transaction()
            response = await self.notification_service.mark_notification_as_seen(id)

            if not response.success:
                await self.notification_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.notification_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Notification marked as seen successfully",
            )
        except Exception as e:
            await self.notification_service.rollback_transaction()
            await self.logger.log(
                action="MarkNotificationAsSeen",
                entity="Notification",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="NotificationController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
