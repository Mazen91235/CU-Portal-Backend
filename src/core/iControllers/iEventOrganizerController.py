from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.eventOrganizerDtos import (
    EventOrganizerCreateDto,
    EventOrganizerUpdateDto,
    EventOrganizerSearchDto,
)


class IEventOrganizerController(
    ICrudController[
        EventOrganizerCreateDto, EventOrganizerUpdateDto, EventOrganizerSearchDto
    ]
):
    pass
