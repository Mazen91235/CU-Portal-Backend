from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.entities.announcement import Announcement
from core.entities.user import User 
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.announcementDtos import (
    AnnouncementCreateDto,
    AnnouncementUpdateDto,
    AnnouncementResponseDto,
    AnnouncementSearchDto,
)


class IAnnouncementService(
    IQueryableService[Announcement, AnnouncementSearchDto],
    IUpdatableService[Announcement],
):
    @abstractmethod
    async def create(self, data: AnnouncementCreateDto) -> BaseResponseDto[AnnouncementResponseDto]:
        pass

    @abstractmethod
    async def update(self, announcement_id: int, data: AnnouncementUpdateDto) -> BaseResponseDto[AnnouncementResponseDto]:
        pass

    @abstractmethod
    async def delete(self, announcement_id: int,) -> BaseResponseDto[bool]:
        pass