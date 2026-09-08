from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.entities.notification import Notification
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userNotificationDtos import UserNotificationSearchDto


class INotificationService(
    IQueryableService[Notification, UserNotificationSearchDto],
    ICreatableService[Notification],
):
    # Notification Specific Methods
    @abstractmethod
    async def mark_notification_as_seen(
        self, notification_id: int
    ) -> BaseResponseDto[bool]:
        pass
