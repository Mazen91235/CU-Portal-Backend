from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController


class INotificationController(IQueryableController):
    # User Controllers
    @abstractmethod
    async def get_notifications_user(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def mark_notification_as_seen(self, request: Request, notification_id: int) -> Response:
        pass