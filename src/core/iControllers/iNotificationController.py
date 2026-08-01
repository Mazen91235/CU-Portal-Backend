from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController


class INotificationController(IQueryableController):
    @abstractmethod
    async def mark_notification_as_seen(self, request: Request) -> Response:
        pass
