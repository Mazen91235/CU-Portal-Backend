from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.announcementDtos import (
    AnnouncementCreateDto,
    AnnouncementUpdateDto,
    AnnouncementSearchDto,
)


class IAnnouncementController(
    ICrudController[AnnouncementCreateDto, AnnouncementUpdateDto, AnnouncementSearchDto]
):
    pass
