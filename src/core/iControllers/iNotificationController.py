from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.dtos.userNotificationDtos import UserNotificationSearchDto
from core.dtos.notificationDtos import NotificationCreateDto


class INotificationController(
    IQueryableController[UserNotificationSearchDto],
    ICreatableController[NotificationCreateDto],
):
    @abstractmethod
    async def mark_notification_as_seen(self, request: Request, id: int) -> Response:
        pass
    
    @abstractmethod
    async def send_reminders(self, request: Request) -> Response:
        pass
