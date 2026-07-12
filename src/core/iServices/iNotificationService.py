from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.entities.userNotification import UserNotification
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userNotificationDtos import UserNotificationSearchDto
from core.models.queryModel import QueryModel


class INotificationService(IQueryableService[UserNotification, UserNotificationSearchDto]):
    # User Specific Methods
    @abstractmethod
    async def get_notifications_user(self, query: QueryModel[UserNotificationSearchDto]) -> BaseResponseDto[list[UserNotification]]:
        pass

    @abstractmethod
    async def mark_notification_as_seen(self, notification_id: int) -> BaseResponseDto[bool]:
        pass