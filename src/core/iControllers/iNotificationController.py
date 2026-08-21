from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.dtos.userNotificationDtos import UserNotificationSearchDto


class INotificationController(IQueryableController[UserNotificationSearchDto]):
    @abstractmethod
    async def mark_notification_as_seen(self, request: Request, id: int) -> Response:
        pass
