from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.entities.notification import Notification
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.notificationDtos import NotificationCreateDto, NotificationMarkManyAsSeenDto
from core.dtos.userNotificationDtos import UserNotificationSearchDto


class INotificationService(IQueryableService[Notification, UserNotificationSearchDto]):
    # Notification Specific Methods
    @abstractmethod
    async def create(self, data: NotificationCreateDto) -> BaseResponseDto:
        pass

    @abstractmethod
    async def mark_notifications_as_seen(
        self, data: NotificationMarkManyAsSeenDto
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def send_reminders(self) -> BaseResponseDto:
        pass
