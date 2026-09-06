from core.iServices.bases.iCrudService import ICrudService
from core.entities.eventOrganizer import EventOrganizer
from core.dtos.eventOrganizerDtos import EventOrganizerSearchDto


class IEventOrganizerService(ICrudService[EventOrganizer, EventOrganizerSearchDto]):
    pass
