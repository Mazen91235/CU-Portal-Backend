from core.entities.eventOrganizer import EventOrganizer
from core.iServices.bases.iCrudService import ICrudService
from core.dtos.eventOrganizerDtos import EventOrganizerSearchDto


class IAnnouncementService(ICrudService[EventOrganizer, EventOrganizerSearchDto]):
    pass