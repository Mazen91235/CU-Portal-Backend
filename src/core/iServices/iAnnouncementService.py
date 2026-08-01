from core.entities.announcement import Announcement
from core.iServices.bases.iCrudService import ICrudService
from core.dtos.announcementDtos import AnnouncementSearchDto


class IAnnouncementService(ICrudService[Announcement, AnnouncementSearchDto]):
    pass